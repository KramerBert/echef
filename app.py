import os
from flask import Flask, request, redirect, url_for, render_template, session, flash, send_file, jsonify
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.local import LocalProxy
from werkzeug.exceptions import HTTPException, InternalServerError
from urllib.parse import quote, urlparse
import logging
import io
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import csv
from datetime import datetime, timedelta
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import requests
from itsdangerous import URLSafeTimedSerializer
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from flask import send_from_directory

load_dotenv()  # Load the values from .env

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
logger.addHandler(ch)

# Create the Flask application instance
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Verplaats dit naar hier, voor create_app()

# Stap 1: Log het bestaan van de environment variabelen (geen gevoelige data)
if app.secret_key:
    logger.debug("SECRET_KEY loaded successfully")
else:
    logger.error("SECRET_KEY is missing")

if app.config.get('SECURITY_PASSWORD_SALT'):
    logger.debug("SECURITY_PASSWORD_SALT loaded successfully")
else:
    logger.error("SECURITY_PASSWORD_SALT is missing")

def create_app():
    """Application factory function"""
    # Configure the app
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config['SECURITY_PASSWORD_SALT'] = os.getenv("SECURITY_PASSWORD_SALT", "your-default-salt")
    
    csrf = CSRFProtect(app)
    
    # Configure session handling
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800
    )

    # Removed blueprint registration; routes are defined below instead.

    return app

# Improved error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.error(f'Page not found: {request.url}')
    return render_template('error.html', error=error), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Server Error: {error}')
    db = get_db_connection()
    if db is not None:
        db.close()
    return render_template('error.html', error=error), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f'Unhandled exception: {str(e)}')
    if isinstance(e, HTTPException):
        return render_template('error.html', error=e), e.code
    
    error = InternalServerError()
    return render_template('error.html', error=error), 500

# Database configuration from .env
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Database configuration
db_url = os.getenv("JAWSDB_URL")  # Gebruik JawsDB URL
if db_url:  # Heroku
    url = urlparse(db_url)
    DB_CONFIG = {
        'host': url.hostname,
        'database': url.path[1:],
        'user': url.username,
        'password': url.password,
        'port': url.port
    }
else:  # Local development
    DB_CONFIG = {
        'host': os.getenv("DB_HOST"),
        'database': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"), 
        'password': os.getenv("DB_PASSWORD"),
        'port': os.getenv("DB_PORT")
    }

def get_db_connection():
    """
    Creates a new database connection using the configuration
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        logger.error(f"Error connecting to the database: {e}")
        return None

# Reset wachtwoord configuratie
app.config['RESET_TOKEN_EXPIRE_MINUTES'] = 30
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True

def send_reset_email(email, token):
    """Stuur een wachtwoord reset email."""
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = email
    msg['Subject'] = "e-Chef Wachtwoord Reset"
    
    # Gebruik HTTPS in productie en HTTP in lokale ontwikkeling
    scheme = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    reset_url = url_for('reset_password', token=token, _external=True, _scheme=scheme)
    
    body = f"""
    Er is een wachtwoord reset aangevraagd voor je e-Chef account.
    Klik op de onderstaande link om je wachtwoord te resetten:
    
    {reset_url}
    
    Deze link verloopt over {app.config['RESET_TOKEN_EXPIRE_MINUTES']} minuten.
    Als je geen reset hebt aangevraagd, kun je deze email negeren.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return False

def generate_confirmation_token(email):
    """Generate email confirmation token"""
    serializer = URLSafeTimedSerializer(app.secret_key)
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    """Verify email confirmation token met extra logging voor debugging op Heroku."""
    logger.debug(f"Attempting to confirm token: {token}")
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
        logger.debug(f"Token confirmed successfully. Email: {email}")
        return email
    except Exception as e:
        logger.error(f"Token confirmation failed: {str(e)}")
        # Debug logging: toon de huidige secret_key en salt, let op dat je deze informatie later weer verwijdert!
        logger.error(f"Token bevestiging mislukt: {str(e)}. SECRET_KEY: {app.secret_key}, SALT: {app.config['SECURITY_PASSWORD_SALT']}")
        return False

def send_confirmation_email(email, token):
    """Send confirmation email"""
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = email
    msg['Subject'] = "e-Chef Email Verificatie"
    
    scheme = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    verify_url = url_for('verify_email', token=token, _external=True, _scheme=scheme)
    
    body = f"""
    Welkom bij e-Chef!
    
    Klik op de onderstaande link om je email adres te verifiëren:
    
    {verify_url}
    
    Deze link verloopt over 1 uur.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return False

class RegistrationForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig Wachtwoord', validators=[DataRequired(), EqualTo('wachtwoord')])
    submit = SubmitField('Registreren')

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Inloggen')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nieuw wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig wachtwoord', 
                                   validators=[DataRequired(), 
                                             EqualTo('password', message='Wachtwoorden moeten overeenkomen')])
    submit = SubmitField('Wachtwoord wijzigen')

class ForgotPasswordForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Link Versturen')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        # Controleer of er daadwerkelijk een e-mail is ingevuld
        if not email:
            flash("Voer een geldig e-mailadres in.", "danger")
            return redirect(url_for('forgot_password'))
        
        conn = get_db_connection()
        if conn is None:
            flash("Databaseverbinding mislukt.", "danger")
            return redirect(url_for('forgot_password'))
        
        cur = conn.cursor(dictionary=True)
        try:
            # Controleer of het e-mailadres bestaat in de database
            cur.execute("SELECT chef_id FROM chefs WHERE email = %s", (email,))
            chef = cur.fetchone()
            if chef is None:
                flash("E-mailadres niet gevonden.", "danger")
                return redirect(url_for('forgot_password'))
            
            # Genereer reset token en stuur reset e-mail
            token = generate_confirmation_token(email)
            if send_reset_email(email, token):
                flash("Een reset link is naar je e-mailadres gestuurd.", "info")
            else:
                flash("Er is een fout opgetreden bij het versturen van de e-mail.", "danger")
        except Exception as e:
            logger.error(f"Error in forgot_password: {str(e)}")
            flash("Er is een fout opgetreden.", "danger")
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    logger.debug(f"Received reset token: {token}")
    if not token or not isinstance(token, str) or len(token) > 128:
        flash("Ongeldige reset link.", "danger")
        return redirect(url_for('login'))
    form = ResetPasswordForm()
    email = confirm_token(token)
    if not email:
        flash("Reset token is ongeldig of verlopen.", "danger")
        logger.error(f"Reset token invalid or expired for token: {token}")
        return redirect(url_for('login'))
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('login'))
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT chef_id FROM chefs WHERE email = %s", (email,))
    chef = cur.fetchone()
    if chef is None:
        flash("E-mailadres niet gevonden.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for('login'))
    if form.validate_on_submit():
        new_password = form.password.data
        cur.execute("UPDATE chefs SET wachtwoord = %s WHERE chef_id = %s",
                    (generate_password_hash(new_password, method='pbkdf2:sha256'), chef['chef_id']))
        conn.commit()
        flash("Je wachtwoord is succesvol gewijzigd!", "success")
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form, token=token)

def get_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])

# -----------------------------------------------------------
#  Homepage (index)
# -----------------------------------------------------------
@app.route('/')
def home():
    """
    Toon de homepage, met bijvoorbeeld een link naar inloggen/registreren.
    """
    return render_template('home.html', form=FlaskForm())  # Zorg voor een home.html template

# -----------------------------------------------------------
#  Over e-Chef
# -----------------------------------------------------------
@app.route('/about')
def about():
    return render_template('about.html', form=FlaskForm())

# -----------------------------------------------------------
#  AVG Privacy Verklaring
# -----------------------------------------------------------
@app.route('/privacy')
def privacy():
    return render_template('privacy.html', form=FlaskForm())

# -----------------------------------------------------------
#  Registreren
# -----------------------------------------------------------
class RegisterForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig Wachtwoord', 
                                   validators=[DataRequired(), 
                                             EqualTo('wachtwoord', message='Wachtwoorden moeten overeenkomen')])
    submit = SubmitField('Registreren')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()  # Let op: gebruik RegisterForm, niet RegistrationForm
    if form.validate_on_submit():
        try:
            naam = secure_filename(form.naam.data)
            email = form.email.data
            wachtwoord = form.wachtwoord.data
            
            # Voeg een extra check toe voor wachtwoord bevestiging
            if form.wachtwoord.data != form.confirm_password.data:
                flash("Wachtwoorden komen niet overeen.", "danger")
                return render_template('register.html', form=form)

            hashed_pw = generate_password_hash(wachtwoord, method='pbkdf2:sha256')

            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor()
            try:
                # Add email_verified column with default value 0
                cur.execute("""
                    INSERT INTO chefs (naam, email, wachtwoord, email_verified)
                    VALUES (%s, %s, %s, 0)
                """, (naam, email, hashed_pw))
                conn.commit()

                # Generate confirmation token and send email
                token = generate_confirmation_token(email)
                if send_confirmation_email(email, token):
                    flash("Registratie succesvol! Check je email om je account te verifiëren.", "success")
                    return redirect(url_for('verify_email'))  # Zonder token parameter
                else:
                    flash("Registratie succesvol, maar er ging iets mis met het versturen van de verificatie email. Neem contact op met support.", "warning")

            except Exception as e:
                conn.rollback()
                logger.error(f'Registration error: {str(e)}')
                flash("Er is een fout opgetreden bij registratie.", "danger")
            finally:
                cur.close()
                conn.close()

        except Exception as e:
            logger.error(f'Registration error: {str(e)}')
            flash("Er is een fout opgetreden.", "danger")

    return render_template('register.html', form=form)

@app.route('/verify-email', methods=['GET'])
@app.route('/verify-email/<token>', methods=['GET'])
def verify_email(token=None):
    """Handle both the initial verification page and token verification"""
    if not token:
        # Show the initial verification page
        return render_template('verify_email.html', verified=False)
    
    # Handle token verification
    email = confirm_token(token)
    if email:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE chefs 
                    SET email_verified = 1 
                    WHERE email = %s
                """, (email,))
                conn.commit()
                flash("Email adres geverifieerd! Je kunt nu inloggen.", "success")
                return render_template('verify_email.html', verified=True)
            except Exception as e:
                conn.rollback()
                logger.error(f'Email verification error: {str(e)}')
                flash("Er is een fout opgetreden bij het verifiëren van je email.", "danger")
            finally:
                cur.close()
                conn.close()
    else:
        flash("Ongeldige of verlopen verificatie link.", "danger")
    
    return render_template('verify_email.html', verified=False)

# -----------------------------------------------------------
#  Inloggen
# -----------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            email = form.email.data
            wachtwoord = form.wachtwoord.data

            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SELECT * FROM chefs WHERE email = %s", (email,))
                chef = cur.fetchone()
                
                if chef and check_password_hash(chef['wachtwoord'], wachtwoord):
                    if not chef.get('email_verified', False):
                        flash("Verifieer eerst je email adres voordat je inlogt.", "warning")
                        return redirect(url_for('verify_email'))
                    
                    session.clear()
                    chef_id = chef.get('chef_id')
                    if chef_id is None:
                        flash("Er is een fout opgetreden bij het inloggen: ongeldige accountgegevens.", "danger")
                        return redirect(url_for('login'))
                    session['chef_id'] = int(chef_id)
                    session['chef_naam'] = chef['naam']
                    session.permanent = True
                    
                    flash("Succesvol ingelogd!", "success")
                    return redirect(url_for('dashboard', chef_naam=chef['naam']))
                else:
                    flash("Ongeldige inloggegevens.", "danger")
            finally:
                cur.close()
                conn.close()
        except Exception as e:
            logger.error(f'Login error: {str(e)}')
            flash("Er is een fout opgetreden bij inloggen.", "danger")

    return render_template('login.html', form=form)

# -----------------------------------------------------------
#  Uitloggen
# -----------------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Je bent uitgelogd.", "info")
    return redirect(url_for('home'))

# -----------------------------------------------------------
#  Persoonlijk Dashboard
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>')
def dashboard(chef_naam):
    """
    Eenvoudig dashboard waarop de chef na inloggen belandt.
    We controleren of de ingelogde chef overeenkomt met de URL.
    """
    try:
        app.logger.info(f"Accessing dashboard for chef: {chef_naam}")
        app.logger.info(f"Session data: {session}")
        
        if 'chef_id' not in session:
            app.logger.warning("No chef_id in session")
            flash("Je bent niet ingelogd.", "warning")
            return redirect(url_for('login'))
            
        if 'chef_naam' not in session:
            app.logger.warning("No chef_naam in session")
            flash("Sessie verlopen.", "warning")
            return redirect(url_for('login'))
            
        if session['chef_naam'] != chef_naam:
            app.logger.warning(f"Chef naam mismatch: {session['chef_naam']} != {chef_naam}")
            flash("Ongeldige sessie. Log opnieuw in.", "warning")
            return redirect(url_for('login'))

        return render_template('dashboard.html', chef_naam=chef_naam)
        
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('login'))

# -----------------------------------------------------------
#  Ingrediënten Beheren
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/ingredients', methods=['GET', 'POST'])
def manage_ingredients(chef_naam):
    form = FlaskForm()  # Add this line for CSRF validation
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            if not form.validate_on_submit():  # Add CSRF validation
                flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
                return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

            naam = request.form.get('naam')
            categorie = request.form.get('categorie')
            eenheid = request.form.get('eenheid')
            prijs_per_eenheid = request.form.get('prijs_per_eenheid')

            # Check for duplicate ingredient
            cur.execute("""
                SELECT * FROM ingredients 
                WHERE chef_id = %s AND naam = %s AND categorie = %s
            """, (session['chef_id'], naam, categorie))
            existing_ingredient = cur.fetchone()

            if existing_ingredient:
                flash("Ingrediënt bestaat al.", "danger")
            else:
                try:
                    cur.execute("""
                        INSERT INTO ingredients (chef_id, naam, categorie, eenheid, prijs_per_eenheid)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (session['chef_id'], naam, categorie, eenheid, prijs_per_eenheid))
                    conn.commit()
                    flash("Ingrediënt toegevoegd!", "success")
                except Exception as e:
                    conn.rollback()
                    flash(f"Fout bij toevoegen ingrediënt: {str(e)}", "danger")

        # Haal unieke categorieën op
        cur.execute("""
            SELECT DISTINCT categorie 
            FROM ingredients 
            WHERE chef_id = %s
        """, (session['chef_id'],))
        unieke_categorieen = [row['categorie'] for row in cur.fetchall()]

        # Haal alle ingrediënten op
        filter_categorie = request.args.get('filter_categorie')
        if filter_categorie:
            cur.execute("""
                SELECT * 
                FROM ingredients 
                WHERE chef_id = %s AND categorie = %s
                ORDER BY ingredient_id DESC
            """, (session['chef_id'], filter_categorie))
        else:
            cur.execute("""
                SELECT * 
                FROM ingredients 
                WHERE chef_id = %s
                ORDER BY ingredient_id DESC
            """, (session['chef_id'],))
        alle_ingredienten = cur.fetchall()

        return render_template('manage_ingredients.html',
                           chef_naam=chef_naam,
                           ingredienten=alle_ingredienten,
                           unieke_categorieen=unieke_categorieen,
                           filter_categorie=filter_categorie,
                           form=form)

    except Exception as e:
        logger.error(f'Error in manage_ingredients: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    finally:
        cur.close()
        conn.close()

@app.route('/dashboard/<chef_naam>/ingredients/bulk_add', methods=['POST'])
def bulk_add_ingredients(chef_naam):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    if 'csv_file' not in request.files:
        flash("Geen bestand geselecteerd.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

    file = request.files['csv_file']
    filename = secure_filename(file.filename)
    if filename == '':
        flash("Geen bestand geselecteerd.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

    if not file.filename.endswith('.csv'):
        flash("Ongeldig bestandstype. Upload een CSV-bestand.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    cur = conn.cursor()

    try:
        csv_reader = csv.reader(io.StringIO(file.stream.read().decode('utf-8')))
        next(csv_reader)  # Skip header row
        for row in csv_reader:
            if len(row) != 4:
                flash("Ongeldig CSV-formaat. Zorg ervoor dat het bestand 4 kolommen bevat: naam, categorie, eenheid, prijs_per_eenheid.", "danger")
                return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

            naam, categorie, eenheid, prijs_per_eenheid = row
            cur.execute("""
                INSERT INTO ingredients (chef_id, naam, categorie, eenheid, prijs_per_eenheid)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['chef_id'], naam, categorie, eenheid, prijs_per_eenheid))
        conn.commit()
        flash("Ingrediënten succesvol toegevoegd!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij toevoegen ingrediënten: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

@app.route('/download_csv_template')
def download_csv_template():
    """
    Serve a CSV template for bulk adding ingredients.
    """
    csv_content = io.StringIO()
    csv_writer = csv_content
    csv_writer.writerow(['naam', 'categorie', 'eenheid', 'prijs_per_eenheid'])
    csv_writer.writerow(['Voorbeeld Naam', 'Voorbeeld Categorie', 'gram (g)', '0.00'])

    csv_content.seek(0)
    return send_file(
        io.BytesIO(csv_content.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='ingredienten_template.csv'
    )

# -----------------------------------------------------------
#  Gerechten Samenstellen
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/dishes', methods=['GET', 'POST'])
def manage_dishes(chef_naam):
    form = FlaskForm()  # Add this line for CSRF validation
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_dishes', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST' and 'gerechtForm' in request.form:
            if not form.validate_on_submit():  # Add CSRF validation
                flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
                return redirect(url_for('manage_dishes', chef_naam=chef_naam))

            naam = request.form.get('naam')
            beschrijving = request.form.get('beschrijving')
            gerecht_categorie = request.form.get('gerecht_categorie')
            bereidingswijze = request.form.get('bereidingswijze')

            try:
                cur.execute("""
                    INSERT INTO dishes (chef_id, naam, beschrijving, categorie, bereidingswijze)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session['chef_id'], naam, beschrijving, gerecht_categorie, bereidingswijze))
                new_dish_id = cur.lastrowid
                conn.commit()
                flash("Gerecht toegevoegd!", "success")
                return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=new_dish_id))
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij toevoegen gerecht: {str(e)}", "danger")

        # Haal alle gerechten van deze chef op
        cur.execute("""
            SELECT * FROM dishes
            WHERE chef_id = %s
            ORDER BY dish_id DESC
        """, (session['chef_id'],))
        alle_gerechten = cur.fetchall()

        return render_template('manage_dishes.html',
                             chef_naam=chef_naam,
                             gerechten=alle_gerechten,
                             form=form)  # Add form to template context

    except Exception as e:
        logger.error(f'Error in manage_dishes: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------
#  Gerecht Bewerken (Ingrediënten toevoegen)
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/dishes/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(chef_naam, dish_id):
    form = FlaskForm()  # Add this line for CSRF validation
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        if not form.validate_on_submit():  # Add CSRF validation
            flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
            return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_dishes', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    # Haal info over het gerecht op (check of het bij deze chef hoort)
    cur.execute("SELECT * FROM dishes WHERE dish_id = %s AND chef_id = %s",
                (dish_id, session['chef_id']))
    gerecht = cur.fetchone()
    if not gerecht:
        cur.close()
        conn.close()
        flash("Gerecht niet gevonden of je hebt geen toestemming.", "danger")
        return redirect(url_for('manage_dishes', chef_naam=chef_naam))

    # Opslaan van nieuw ingrediënt voor dit gerecht
    if request.method == 'POST':
        if 'updateForm' in request.form:
            nieuwe_naam = request.form.get('naam')
            nieuwe_beschrijving = request.form.get('beschrijving')
            nieuwe_verkoopprijs = request.form.get('verkoopprijs')
            nieuwe_categorie = request.form.get('gerecht_categorie')
            nieuwe_bereidingswijze = request.form.get('bereidingswijze')

            try:
                cur.execute("""
                    UPDATE dishes
                    SET naam = %s, beschrijving = %s, verkoopprijs = %s, categorie = %s, bereidingswijze = %s
                    WHERE dish_id = %s AND chef_id = %s
                """, (nieuwe_naam, nieuwe_beschrijving, nieuwe_verkoopprijs, nieuwe_categorie, nieuwe_bereidingswijze, dish_id, session['chef_id']))
                conn.commit()
                flash("Gerecht bijgewerkt!", "success")
                return redirect(url_for('all_dishes'))
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij bijwerken gerecht: {str(e)}", "danger")
        elif 'ingredientForm' in request.form:
            ingredient_id = request.form.get('ingredient_id')
            hoeveelheid = request.form.get('hoeveelheid')

            # Bepaal prijs_totaal (hoeveelheid * prijs_per_eenheid)
            cur.execute("""
                SELECT prijs_per_eenheid 
                FROM ingredients 
                WHERE ingredient_id = %s 
                  AND chef_id = %s
            """, (ingredient_id, session['chef_id']))
            ingredient_info = cur.fetchone()
            if ingredient_info:
                prijs_per_eenheid = ingredient_info['prijs_per_eenheid']
                prijs_totaal = float(hoeveelheid) * float(prijs_per_eenheid)

                try:
                    cur.execute("""
                        INSERT INTO dish_ingredients (dish_id, ingredient_id, hoeveelheid, prijs_totaal)
                        VALUES (%s, %s, %s, %s)
                    """, (dish_id, ingredient_id, hoeveelheid, prijs_totaal))
                    conn.commit()
                    flash("Ingrediënt toegevoegd aan het gerecht!", "success")
                except Exception as e:
                    conn.rollback()
                    flash(f"Fout bij toevoegen van ingrediënt: {str(e)}", "danger")
            else:
                flash("Ongeldig ingrediënt of geen toegang.", "danger")
        elif 'descriptionForm' in request.form:
            nieuwe_beschrijving = request.form.get('beschrijving')
            try:
                cur.execute("""
                    UPDATE dishes
                    SET beschrijving = %s
                    WHERE dish_id = %s AND chef_id = %s
                """, (nieuwe_beschrijving, dish_id, session['chef_id']))
                conn.commit()
                flash("Beschrijving bijgewerkt!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij bijwerken beschrijving: {str(e)}", "danger")
        elif 'nameForm' in request.form:
            nieuwe_naam = request.form.get('naam')
            try:
                cur.execute("""
                    UPDATE dishes
                    SET naam = %s
                    WHERE dish_id = %s AND chef_id = %s
                """, (nieuwe_naam, dish_id, session['chef_id']))
                conn.commit()
                flash("Naam bijgewerkt!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij bijwerken naam: {str(e)}", "danger")
        elif 'priceForm' in request.form:
            nieuwe_verkoopprijs = request.form.get('verkoopprijs')
            try:
                cur.execute("""
                    UPDATE dishes
                    SET verkoopprijs = %s
                    WHERE dish_id = %s AND chef_id = %s
                """, (nieuwe_verkoopprijs, dish_id, session['chef_id']))
                conn.commit()
                flash("Verkoopprijs bijgewerkt!", "success")
                return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id) + '#verkoopprijs-sectie')
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij bijwerken verkoopprijs: {str(e)}", "danger")
        elif 'methodForm' in request.form:
            nieuwe_bereidingswijze = request.form.get('bereidingswijze')
            try:
                cur.execute("""
                    UPDATE dishes
                    SET bereidingswijze = %s
                    WHERE dish_id = %s AND chef_id = %s
                """, (nieuwe_bereidingswijze, dish_id, session['chef_id']))
                conn.commit()
                flash("Bereidingswijze bijgewerkt!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij bijwerken bereidingswijze: {str(e)}", "danger")

    # Haal alle beschikbare ingrediënten van deze chef op
    cur.execute("""
        SELECT * 
        FROM ingredients 
        WHERE chef_id = %s
        ORDER BY naam ASC
    """, (session['chef_id'],))
    alle_ingredienten = cur.fetchall()

    # Haal de gekoppelde ingrediënten voor dit gerecht op
    cur.execute("""
        SELECT di.*, i.naam AS ingredient_naam, i.eenheid, i.prijs_per_eenheid
        FROM dish_ingredients di
        JOIN ingredients i ON di.ingredient_id = i.ingredient_id
        WHERE di.dish_id = %s
    """, (dish_id,))
    gerecht_ingredienten = cur.fetchall()

    # Eventuele totale kostprijs (op basis van dish_ingredients.prijs_totaal)
    totaal_ingredient_prijs = sum([gi['prijs_totaal'] for gi in gerecht_ingredienten])

    # Haal alle beschikbare allergenen op
    cur.execute("SELECT * FROM allergenen ORDER BY naam")
    alle_allergenen = cur.fetchall()
    
    # Haal de geselecteerde allergenen voor dit gerecht op
    cur.execute("""
        SELECT allergeen_id FROM dish_allergenen
        WHERE dish_id = %s
    """, (dish_id,))
    gerecht_allergenen = [row['allergeen_id'] for row in cur.fetchall()]

    # Haal alle beschikbare diëten op
    cur.execute("SELECT * FROM dieten ORDER BY naam")
    alle_dieten = cur.fetchall()
    
    # Haal de geselecteerde diëten voor dit gerecht op
    cur.execute("""
        SELECT dieet_id FROM dish_dieten
        WHERE dish_id = %s
    """, (dish_id,))
    gerecht_dieten = [row['dieet_id'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template(
        'edit_dish.html',
        chef_naam=chef_naam,
        gerecht=gerecht,
        alle_ingredienten=alle_ingredienten,
        gerecht_ingredienten=gerecht_ingredienten,
        totaal_ingredient_prijs=totaal_ingredient_prijs,
        alle_allergenen=alle_allergenen,
        gerecht_allergenen=gerecht_allergenen,
        alle_dieten=alle_dieten,
        gerecht_dieten=gerecht_dieten,
        form=form  # Add form to template context
    )

@app.route('/chef/<chef_naam>/dish/<int:dish_id>/ingredient/<int:ingredient_id>/update', methods=['POST'])
def update_dish_ingredient(chef_naam, dish_id, ingredient_id):
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))
    
    cur = conn.cursor(dictionary=True)
    try:
        nieuwe_hoeveelheid = float(request.form['nieuwe_hoeveelheid'])
        
        # Eerst de prijs_per_eenheid ophalen
        cur.execute("""
            SELECT prijs_per_eenheid 
            FROM ingredients 
            WHERE ingredient_id = %s
        """, (ingredient_id,))
        ingredient = cur.fetchone()
        
        if ingredient:
            nieuwe_prijs_totaal = nieuwe_hoeveelheid * float(ingredient['prijs_per_eenheid'])
            
            # Update de hoeveelheid en prijs_totaal
            cur.execute("""
                UPDATE dish_ingredients 
                SET hoeveelheid = %s, prijs_totaal = %s
                WHERE dish_id = %s AND ingredient_id = %s
            """, (nieuwe_hoeveelheid, nieuwe_prijs_totaal, dish_id, ingredient_id))
            
            conn.commit()
            flash("Ingrediënt hoeveelheid bijgewerkt!", "success")
        else:
            flash("Ingrediënt niet gevonden.", "danger")
            
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij bijwerken: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id) + '#ingredienten-tabel')

@app.route('/chef/<chef_naam>/dish/<int:dish_id>/ingredient/<int:ingredient_id>/remove', methods=['POST'])
def remove_dish_ingredient(chef_naam, dish_id, ingredient_id):
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))
    
    cur = conn.cursor()
    try:
        # Verwijder het ingredient uit het gerecht
        cur.execute("""
            DELETE FROM dish_ingredients 
            WHERE dish_id = %s AND ingredient_id = %s
        """, (dish_id, ingredient_id))
        
        conn.commit()
        flash("Ingrediënt verwijderd uit gerecht!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij verwijderen: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id) + '#ingredienten-tabel')

@app.route('/dashboard/<chef_naam>/dish/<int:dish_id>/allergenen', methods=['POST'])
def update_dish_allergenen(chef_naam, dish_id):
    form = FlaskForm()  # Add CSRF validation
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Verwijder bestaande allergenen voor dit gerecht
        cur.execute("DELETE FROM dish_allergenen WHERE dish_id = %s", (dish_id,))
        
        # Voeg nieuwe allergenen toe
        nieuwe_allergenen = request.form.getlist('allergenen[]')
        for allergeen_id in nieuwe_allergenen:
            cur.execute("""
                INSERT INTO dish_allergenen (dish_id, allergeen_id)
                VALUES (%s, %s)
            """, (dish_id, allergeen_id))
        
        conn.commit()
        flash("Allergenen bijgewerkt!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij bijwerken allergenen: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

@app.route('/dashboard/<chef_naam>/dish/<int:dish_id>/dieten', methods=['POST'])
def update_dish_dieten(chef_naam, dish_id):
    form = FlaskForm()  # Add CSRF validation
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Verwijder bestaande diëten voor dit gerecht
        cur.execute("DELETE FROM dish_dieten WHERE dish_id = %s", (dish_id,))
        
        # Voeg nieuwe diëten toe
        nieuwe_dieten = request.form.getlist('dieten[]')
        for dieet_id in nieuwe_dieten:
            cur.execute("""
                INSERT INTO dish_dieten (dish_id, dieet_id)
                VALUES (%s, %s)
            """, (dish_id, dieet_id))
        
        conn.commit()
        flash("Diëten bijgewerkt!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij bijwerken diëten: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('edit_dish', chef_naam=chef_naam, dish_id=dish_id))

# -----------------------------------------------------------
#  Alle Gerechten Beheren
# -----------------------------------------------------------
@app.route('/all_dishes')
def all_dishes():
    """
    Pagina om alle gerechten te beheren.
    """
    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('home'))
    cur = conn.cursor(dictionary=True)

    # Aangepaste query om alleen gerechten van de ingelogde chef te tonen
    cur.execute("""
        SELECT d.*, c.naam as chef_naam, 
               (SELECT SUM(di.prijs_totaal) 
                FROM dish_ingredients di 
                WHERE di.dish_id = d.dish_id) as totaal_ingredient_prijs
        FROM dishes d
        JOIN chefs c ON d.chef_id = c.chef_id
        WHERE d.chef_id = %s  /* Voeg deze WHERE clausule toe */
        ORDER BY d.dish_id DESC
    """, (session['chef_id'],))
    
    alle_gerechten = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('all_dishes.html', 
                         gerechten=alle_gerechten,
                         form=FlaskForm())  # Add form to template context

# -----------------------------------------------------------
#  Export Dishes to MS Word
# -----------------------------------------------------------
@app.route('/export_dishes', methods=['POST'])
def export_dishes():
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger")
        return redirect(url_for('all_dishes'))

    """
    Export selected dishes to a Microsoft Word document.
    """
    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    selected_dish_ids = request.form.getlist('selected_dishes')
    if not selected_dish_ids:
        flash("Geen gerechten geselecteerd.", "danger")
        return redirect(url_for('all_dishes'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('all_dishes'))
    cur = conn.cursor(dictionary=True)

    try:
        # Haal alleen de geselecteerde gerechten van de ingelogde chef op
        format_strings = ','.join(['%s'] * len(selected_dish_ids))
        query = """
            SELECT d.*, c.naam as chef_naam, 
                   (SELECT SUM(di.prijs_totaal) 
                    FROM dish_ingredients di 
                    WHERE di.dish_id = d.dish_id) as totaal_ingredient_prijs
            FROM dishes d
            JOIN chefs c ON d.chef_id = c.chef_id
            WHERE d.dish_id IN ({}) AND d.chef_id = %s
            ORDER BY d.categorie
        """.format(format_strings)
        
        params = selected_dish_ids + [session['chef_id']]
        cur.execute(query, tuple(params))
        selected_dishes = cur.fetchall()

        # Maak een Word-document aan
        doc = Document()
        doc.add_heading('Menukaart', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Groepeer gerechten per categorie
        current_category = None
        for dish in selected_dishes:
            # Voeg categorieheader toe als we een nieuwe categorie tegenkomen
            if dish['categorie'] != current_category:
                current_category = dish['categorie']
                doc.add_heading(current_category, level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Voeg gerechtnaam en prijs toe
            verkoopprijs = dish['verkoopprijs'] if dish['verkoopprijs'] else 'n.v.t.'
            naam = dish['naam'] if dish['naam'] else 'Onbekend gerecht'
            price_paragraph = doc.add_paragraph()
            price_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            price_paragraph.add_run(f"{naam} - €{verkoopprijs}").bold = True

            # Voeg beschrijving toe
            if dish['beschrijving']:
                desc_paragraph = doc.add_paragraph(dish['beschrijving'])
                desc_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Haal allergenen op voor dit gerecht
            cur.execute("""
                SELECT a.naam, a.icon_class 
                FROM allergenen a
                JOIN dish_allergenen da ON a.allergeen_id = da.allergeen_id
                WHERE da.dish_id = %s
                ORDER BY a.naam
            """, (dish['dish_id'],))
            allergenen = cur.fetchall()

            # Voeg allergenen toe als ze bestaan
            if allergenen:
                allergenen_paragraph = doc.add_paragraph()
                allergenen_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                allergenen_text = "Allergenen: " + ", ".join([a['naam'] for a in allergenen])
                allergenen_paragraph.add_run(allergenen_text).italic = True

            # Voeg diëten toe aan het document
            cur.execute("""
                SELECT d.naam, d.icon_class 
                FROM dieten d
                JOIN dish_dieten dd ON d.dieet_id = dd.dieet_id
                WHERE dd.dish_id = %s
                ORDER BY d.naam
            """, (dish['dish_id'],))
            dieten = cur.fetchall()
            
            if dieten:
                dieten_paragraph = doc.add_paragraph()
                dieten_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                dieten_text = "Geschikt voor: " + ", ".join([d['naam'] for d in dieten])
                dieten_paragraph.add_run(dieten_text).italic = True

            # Voeg witruimte toe tussen gerechten
            doc.add_paragraph()

        # Sla het document op in een in-memory buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='Menukaart.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        logger.error(f'Error exporting dishes: {str(e)}')
        flash("Er is een fout opgetreden bij het exporteren van de menukaart.", "danger")
        return redirect(url_for('all_dishes'))
    
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------
#  Export Cookbook to MS Word
# -----------------------------------------------------------
@app.route('/export_cookbook', methods=['POST'])
def export_cookbook():
    """
    Export all dishes to a Microsoft Word document as a cookbook.
    """
    form = FlaskForm()  # Add CSRF validation
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('all_dishes'))

    if 'chef_id' not in session:  # Add this check
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('all_dishes'))
    cur = conn.cursor(dictionary=True)

    # Haal alle gerechten van de ingelogde chef op
    cur.execute("""
        SELECT d.*, c.naam as chef_naam, 
               (SELECT SUM(di.prijs_totaal) 
                FROM dish_ingredients di 
                WHERE di.dish_id = d.dish_id) as totaal_ingredient_prijs
        FROM dishes d
        JOIN chefs c ON d.chef_id = c.chef_id
        WHERE d.chef_id = %s
        ORDER BY CASE 
            WHEN d.categorie = 'Amuse-bouche' THEN 1
            WHEN d.categorie = 'Hors-d''oeuvre' THEN 2
            WHEN d.categorie = 'Potage' THEN 3
            WHEN d.categorie = 'Poisson' THEN 4
            WHEN d.categorie = 'Entrée' THEN 5
            WHEN d.categorie = 'Sorbet' THEN 6
            WHEN d.categorie = 'Relevé of Rôti' THEN 7
            WHEN d.categorie = 'Légumes / Groentegerecht' THEN 8
            WHEN d.categorie = 'Salade' THEN 9
            WHEN d.categorie = 'Fromage' THEN 10
            WHEN d.categorie = 'Entremets' THEN 11
            WHEN d.categorie = 'Café / Mignardises' THEN 12
            WHEN d.categorie = 'Digestief' THEN 13
            ELSE 14
        END
    """, (session['chef_id'],))
    all_dishes = cur.fetchall()

    # Maak een Word-document aan
    doc = Document()
    doc.add_heading('Kookboek', 0).alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Voeg een inhoudsopgave toe
    doc.add_heading('Inhoudsopgave', level=1)
    for dish in all_dishes:
        doc.add_paragraph(dish['naam'], style='List Number')

    doc.add_page_break()

    # Voeg veiligheidscontroles toe voor alle velden
    for dish in all_dishes:
        verkoopprijs = dish['verkoopprijs'] if dish['verkoopprijs'] else 'n.v.t.'
        naam = dish['naam'] if dish['naam'] else 'Onbekend gerecht'
        heading = doc.add_heading(f"{naam} - €{verkoopprijs}", level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

        description_text = dish['beschrijving'] if dish['beschrijving'] else 'Geen beschrijving'
        description = doc.add_paragraph(description_text)
        description.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Haal de ingrediënten voor dit gerecht op
        cur.execute("""
            SELECT di.*, i.naam AS ingredient_naam, i.eenheid
            FROM dish_ingredients di
            JOIN ingredients i ON di.ingredient_id = i.ingredient_id
            WHERE di.dish_id = %s
        """, (dish['dish_id'],))
        gerecht_ingredienten = cur.fetchall()

        if gerecht_ingredienten:
            doc.add_heading('Ingrediënten', level=2)
            for gi in gerecht_ingredienten:
                ingredient_text = f"{gi['hoeveelheid']} {gi['eenheid']} {gi['ingredient_naam']}"
                doc.add_paragraph(ingredient_text).alignment = WD_ALIGN_PARAGRAPH.LEFT

        method_text = dish['bereidingswijze'] if dish['bereidingswijze'] else 'Geen bereidingswijze'
        doc.add_heading('Bereidingswijze', level=2)
        method = doc.add_paragraph(method_text)
        method.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Haal allergenen op voor dit gerecht
        cur.execute("""
            SELECT a.naam, a.icon_class 
            FROM allergenen a
            JOIN dish_allergenen da ON a.allergeen_id = da.allergeen_id
            WHERE da.dish_id = %s
            ORDER BY a.naam
        """, (dish['dish_id'],))
        allergenen = cur.fetchall()

        # Voeg allergenen toe als ze bestaan
        if allergenen:
            allergenen_paragraph = doc.add_paragraph()
            allergenen_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            allergenen_text = "Allergenen: " + ", ".join([a['naam'] for a in allergenen])
            allergenen_paragraph.add_run(allergenen_text).italic = True

        # Voeg diëten toe aan het document
        cur.execute("""
            SELECT d.naam, d.icon_class 
            FROM dieten d
            JOIN dish_dieten dd ON d.dieet_id = dd.dieet_id
            WHERE dd.dish_id = %s
            ORDER BY d.naam
        """, (dish['dish_id'],))
        dieten = cur.fetchall()
        
        if dieten:
            dieten_paragraph = doc.add_paragraph()
            dieten_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            dieten_text = "Geschikt voor: " + ", ".join([d['naam'] for d in dieten])
            dieten_paragraph.add_run(dieten_text).italic = True

        doc.add_paragraph("\n").alignment = WD_ALIGN_PARAGRAPH.LEFT

    cur.close()
    conn.close()

    # Sla het document op in een in-memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    safe_filename = quote('Kookboek.docx', safe='')
    return send_file(
        buffer,
        as_attachment=True, 
        download_name=safe_filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

# -----------------------------------------------------------
#  Verwijder Gerecht
# -----------------------------------------------------------
@app.route('/delete_dish/<int:dish_id>', methods=['POST'])
def delete_dish(dish_id):
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger")
        return redirect(url_for('all_dishes'))

    """
    Verwijder een gerecht.
    """
    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('all_dishes'))
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM dish_ingredients WHERE dish_id = %s", (dish_id,))
        cur.execute("DELETE FROM dishes WHERE dish_id = %s AND chef_id = %s", (dish_id, session['chef_id']))
        conn.commit()
        flash("Gerecht succesvol verwijderd!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij verwijderen gerecht: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('all_dishes'))

# -----------------------------------------------------------
#  Ingrediënt Bewerken
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/ingredients/<int:ingredient_id>', methods=['GET', 'POST'])
def edit_ingredient(chef_naam, ingredient_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    # Haal info over het ingrediënt op (check of het bij deze chef hoort)
    cur.execute("SELECT * FROM ingredients WHERE ingredient_id = %s AND chef_id = %s",
                (ingredient_id, session['chef_id']))
    ingredient = cur.fetchone()
    if not ingredient:
        cur.close()
        conn.close()
        flash("Ingrediënt niet gevonden of je hebt geen toestemming.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

    if request.method == 'POST':
        naam = request.form.get('naam')
        categorie = request.form.get('categorie')
        eenheid = request.form.get('eenheid')
        prijs_per_eenheid = request.form.get('prijs_per_eenheid')

        try:
            # Update het ingrediënt
            cur.execute("""
                UPDATE ingredients
                SET naam = %s, categorie = %s, eenheid = %s, prijs_per_eenheid = %s
                WHERE ingredient_id = %s AND chef_id = %s
            """, (naam, categorie, eenheid, prijs_per_eenheid, ingredient_id, session['chef_id']))

            # Update alle gekoppelde gerechten
            cur.execute("""
                UPDATE dish_ingredients di
                SET prijs_totaal = di.hoeveelheid * %s
                WHERE di.ingredient_id = %s
            """, (prijs_per_eenheid, ingredient_id))
            
            conn.commit()
            flash("Ingrediënt en alle gekoppelde gerechten bijgewerkt!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij bijwerken ingrediënt: {str(e)}", "danger")

        # Haal alle gerechten op waarin dit ingrediënt wordt gebruikt
        cur.execute("""
            SELECT d.naam, di.hoeveelheid, di.prijs_totaal
            FROM dishes d
            JOIN dish_ingredients di ON d.dish_id = di.dish_id
            WHERE di.ingredient_id = %s
        """, (ingredient_id,))
        gerechten_met_ingredient = cur.fetchall()

        cur.close()
        conn.close()
        return redirect(url_for('edit_ingredient', chef_naam=chef_naam, ingredient_id=ingredient_id))

    cur.close()
    conn.close()

    return render_template('edit_ingredient.html', chef_naam=chef_naam, ingredient=ingredient, form=FlaskForm())

# -----------------------------------------------------------
#  Ingrediënt Verwijderen
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/ingredients/<int:ingredient_id>/delete', methods=['POST'])
def delete_ingredient(chef_naam, ingredient_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM ingredients WHERE ingredient_id = %s AND chef_id = %s", (ingredient_id, session['chef_id']))
        conn.commit()
        flash("Ingrediënt succesvol verwijderd!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij verwijderen ingrediënt: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

# -----------------------------------------------------------
#  Export Dish to MS Word
# -----------------------------------------------------------
@app.route('/export_dish/<chef_naam>/<dish_id>', methods=['POST'])
def export_dish(chef_naam, dish_id):
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger") 
        return redirect(url_for('all_dishes'))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_dishes', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)
    try:
        # Haal gerecht informatie op
        cur.execute("""
            SELECT * FROM dishes 
            WHERE dish_id = %s AND chef_id = %s
        """, (dish_id, session['chef_id']))
        gerecht = cur.fetchone()
        
        if not gerecht:
            flash("Gerecht niet gevonden of geen toegang.", "danger")
            return redirect(url_for('all_dishes'))

        # Haal ingrediënten op
        cur.execute("""
            SELECT di.hoeveelheid, i.naam AS ingredient_naam, i.eenheid
            FROM dish_ingredients di
            JOIN ingredients i ON di.ingredient_id = i.ingredient_id
            WHERE di.dish_id = %s
        """, (dish_id,))
        gerecht_ingredienten = cur.fetchall()

        # Maak Word document
        doc = Document()
        doc.add_heading(f"{gerecht['naam']} - Receptuur", level=1)
        
        if gerecht['beschrijving']:
            doc.add_heading('Beschrijving', level=2)
            doc.add_paragraph(gerecht['beschrijving'])
        
        # Voeg ingrediëntenlijst toe
        doc.add_heading('Ingrediënten', level=2)
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        
        # Tabel headers
        header_cells = table.rows[0].cells
        header_cells[0].text = 'Ingrediënt'
        header_cells[1].text = 'Hoeveelheid'
        header_cells[2].text = 'Eenheid'

        # Voeg ingrediënten toe aan tabel
        for ingredient in gerecht_ingredienten:
            row_cells = table.add_row().cells
            row_cells[0].text = ingredient['ingredient_naam']
            row_cells[1].text = str(ingredient['hoeveelheid'])
            row_cells[2].text = ingredient['eenheid']

        if gerecht['bereidingswijze']:
            doc.add_heading('Bereidingswijze', level=2)
            doc.add_paragraph(gerecht['bereidingswijze'])

        # Sla document op in memory
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        filename = f"{gerecht['naam']}_recept.docx"
        safe_filename = secure_filename(filename)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        logger.error(f'Error exporting dish: {str(e)}')
        flash("Er is een fout opgetreden bij het exporteren van het recept.", "danger")
        return redirect(url_for('all_dishes'))
    
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------
#  Werkinstructie
# -----------------------------------------------------------
@app.route('/instructions')
def instructions():
    return render_template('instructions.html', form=FlaskForm())

# -----------------------------------------------------------
# Voeg error handler toe voor Werkzeug exceptions
# @app.errorhandler(HTTPException)
# def handle_exception(e):
#     return
# ...existing code...

# -----------------------------------------------------------
#  Bestellijst Beheren
# -----------------------------------------------------------
@app.route('/orderlist', methods=['GET', 'POST'])
def manage_orderlist():
    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('home'))
    cur = conn.cursor(dictionary=True)

    # Aangepaste query om alleen gerechten van de ingelogde chef te tonen
    cur.execute("""
        SELECT d.*, c.naam as chef_naam
        FROM dishes d
        JOIN chefs c ON d.chef_id = c.chef_id
        WHERE d.chef_id = %s
        ORDER BY d.naam
    """, (session['chef_id'],))
    
    alle_gerechten = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('manage_orderlist.html', gerechten=alle_gerechten, form=FlaskForm())

@app.route('/export_orderlist', methods=['POST'])
def export_orderlist():
    form = FlaskForm()  # Add CSRF validation
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('manage_orderlist'))

    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    dish_quantities = {}
    for key, value in request.form.items():
        if key.startswith('quantity_') and value and int(value) > 0:
            dish_id = int(key.replace('quantity_', ''))
            dish_quantities[dish_id] = int(value)

    if not dish_quantities:
        flash("Geen gerechten geselecteerd.", "warning")
        return redirect(url_for('manage_orderlist'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_orderlist'))
    
    cur = conn.cursor(dictionary=True)

    try:
        total_cost = 0  # Variabele voor totale kostprijs
        ingredient_total = 0  # Verplaatst naar hier voor betere scope

        # Gebruik een dictionary met tuple als key voor de ingrediënten
        total_ingredients = {}
        dishes_info = {}

        for dish_id, quantity in dish_quantities.items():
            # Haal gerecht informatie op
            cur.execute("""
                SELECT * FROM dishes 
                WHERE dish_id = %s
            """, (dish_id,))
            dish = cur.fetchone()
            
            if dish:  # Voeg veiligheidscheck toe
                dishes_info[dish_id] = {
                    'naam': dish['naam'], 
                    'aantal': quantity,
                    'verkoopprijs': float(dish['verkoopprijs'] or 0)
                }
                # Bereken totale verkoopprijs
                total_cost += dishes_info[dish_id]['verkoopprijs'] * quantity

                # Haal ingrediënten voor dit gerecht op met foutafhandeling
                try:
                    cur.execute("""
                        SELECT di.hoeveelheid, 
                               i.naam AS ingredient_naam, 
                               i.eenheid, 
                               i.prijs_per_eenheid
                        FROM dish_ingredients di
                        JOIN ingredients i ON di.ingredient_id = i.ingredient_id
                        WHERE di.dish_id = %s
                    """, (dish_id,))
                    
                    ingredients = cur.fetchall()
                    for ing in ingredients:
                        key = (
                            ing['ingredient_naam'],
                            ing['eenheid'],
                            float(ing['prijs_per_eenheid'] or 0)
                        )
                        if key not in total_ingredients:
                            total_ingredients[key] = 0
                        total_ingredients[key] += float(ing['hoeveelheid']) * quantity
                except Exception as e:
                    logger.error(f'Error processing ingredients for dish {dish_id}: {str(e)}')
                    continue

        # Maak Word document
        doc = Document()
        doc.add_heading('Bestellijst', 0)

        # Voeg bestelde gerechten toe
        doc.add_heading('Verwachtte verkoop:', level=1)
        for dish_info in dishes_info.values():
            doc.add_paragraph(f"{dish_info['naam']}: {dish_info['aantal']}x @ €{dish_info['verkoopprijs']:.2f}")

        # Voeg totale ingrediëntenlijst toe
        doc.add_heading('Benodigde Ingrediënten:', level=1)
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        
        # Headers
        header_cells = table.rows[0].cells
        header_cells[0].text = 'Ingrediënt'
        header_cells[1].text = 'Totaal'
        header_cells[2].text = 'Eenheid'
        header_cells[3].text = 'Prijs per eenheid'
        header_cells[4].text = 'Totaalprijs'

        # Voeg ingrediënten toe met foutafhandeling
        ingredient_total = 0
        for (naam, eenheid, prijs_per_eenheid), hoeveelheid in sorted(total_ingredients.items()):
            try:
                row_cells = table.add_row().cells
                row_cells[0].text = str(naam)
                row_cells[1].text = f"{hoeveelheid:.2f}"
                row_cells[2].text = str(eenheid)
                row_cells[3].text = f"€{prijs_per_eenheid:.2f}"
                subtotal = hoeveelheid * prijs_per_eenheid
                row_cells[4].text = f"€{subtotal:.2f}"
                ingredient_total += subtotal
            except Exception as e:
                logger.error(f'Error adding ingredient {naam} to table: {str(e)}')
                continue

        # Voeg financieel overzicht toe
        doc.add_heading('Financieel Overzicht:', level=1)
        
        # Ingrediëntenkosten
        cost_table = doc.add_table(rows=1, cols=2)
        cost_table.style = 'Table Grid'
        cost_row = cost_table.rows[0].cells
        cost_row[0].text = 'Totale Ingrediëntenkosten:'
        cost_row[1].text = f"€{ingredient_total:.2f}"

        # Verwachte verkoopprijs
        price_row = cost_table.add_row().cells
        price_row[0].text = 'Verwachte Verkoopprijs:'
        price_row[1].text = f"€{total_cost:.2f}"

        # Verwachte winst
        expected_profit = total_cost - ingredient_total
        profit_row = cost_table.add_row().cells
        profit_row[0].text = 'Verwachte Winst:'
        profit_row[1].text = f"€{expected_profit:.2f}"

        # Exporteer document
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='bestellijst.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        logger.error(f'Error creating orderlist: {str(e)}')
        flash("Er is een fout opgetreden bij het maken van de bestellijst.", "danger")
        return redirect(url_for('manage_orderlist'))
    
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------
#  HACCP Module
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/haccp')
def haccp_dashboard(chef_naam):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    # Haal HACCP checklists op met extra informatie
    cur.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) 
                FROM haccp_metingen m 
                JOIN haccp_checkpunten p ON m.punt_id = p.punt_id 
                WHERE p.checklist_id = c.checklist_id 
                AND DATE(m.timestamp) = CURDATE()) as metingen_vandaag,
               DATEDIFF(CURDATE(), 
                       IFNULL((SELECT MAX(DATE(m.timestamp))
                              FROM haccp_metingen m
                              JOIN haccp_checkpunten p ON m.punt_id = p.punt_id
                              WHERE p.checklist_id = c.checklist_id), 
                              '1970-01-01')) as dagen_sinds_laatste_meting
        FROM haccp_checklists c
        WHERE c.chef_id = %s
        ORDER BY c.created_at DESC
    """, (session['chef_id'],))
    checklists = cur.fetchall()

    # Haal laatste metingen op
    cur.execute("""
        SELECT m.*, c.omschrijving, c.grenswaarde
        FROM haccp_metingen m
        JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
        WHERE m.chef_id = %s
        ORDER BY m.timestamp DESC
        LIMIT 10
    """, (session['chef_id'],))
    laatste_metingen = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('haccp/dashboard.html',
                         chef_naam=chef_naam,
                         checklists=checklists,
                         laatste_metingen=laatste_metingen)

@app.route('/dashboard/<chef_naam>/haccp/new_checklist', methods=['GET', 'POST'])
def new_haccp_checklist(chef_naam):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        naam = request.form.get('naam')
        frequentie = request.form.get('frequentie')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO haccp_checklists (chef_id, naam, frequentie)
                VALUES (%s, %s, %s)
            """, (session['chef_id'], naam, frequentie))
            checklist_id = cur.lastrowid
            
            # Voeg checkpunten toe
            checkpunten = request.form.getlist('checkpunt[]')
            grenswaarden = request.form.getlist('grenswaarde[]')
            acties = request.form.getlist('actie[]')
            
            for i in range(len(checkpunten)):
                cur.execute("""
                    INSERT INTO haccp_checkpunten 
                    (checklist_id, omschrijving, grenswaarde, corrigerende_actie)
                    VALUES (%s, %s, %s, %s)
                """, (checklist_id, checkpunten[i], grenswaarden[i], acties[i]))
            
            conn.commit()
            flash("HACCP-checklist aangemaakt!", "success")
            
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij aanmaken checklist: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
            
        return redirect(url_for('haccp_dashboard', chef_naam=chef_naam))
        
    return render_template('haccp/new_checklist.html', chef_naam=chef_naam, form=FlaskForm())

@app.route('/dashboard/<chef_naam>/haccp/checklist/<int:checklist_id>/fill', methods=['GET', 'POST'])
def fill_haccp_checklist(chef_naam, checklist_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('haccp_dashboard', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)

    try:
        # Haal checklist informatie op
        cur.execute("""
            SELECT * FROM haccp_checklists 
            WHERE checklist_id = %s AND chef_id = %s
        """, (checklist_id, session['chef_id']))
        checklist = cur.fetchone()

        if not checklist:
            flash("Checklist niet gevonden.", "danger")
            return redirect(url_for('haccp_dashboard', chef_naam=chef_naam))

        # Haal alle checkpunten op
        cur.execute("""
            SELECT * FROM haccp_checkpunten
            WHERE checklist_id = %s
        """, (checklist_id,))
        checkpunten = cur.fetchall()

        if request.method == 'POST':
            for punt in checkpunten:
                waarde = request.form.get(f'waarde_{punt["punt_id"]}')
                opmerking = request.form.get(f'opmerking_{punt["punt_id"]}')
                actie = request.form.get(f'actie_{punt["punt_id"]}')

                if waarde:  # Alleen opslaan als er een waarde is ingevuld
                    cur.execute("""
                        INSERT INTO haccp_metingen 
                        (punt_id, chef_id, waarde, opmerking, actie_ondernomen)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (punt['punt_id'], session['chef_id'], waarde, opmerking, actie))

            conn.commit()
            flash("HACCP metingen opgeslagen!", "success")
            return redirect(url_for('haccp_dashboard', chef_naam=chef_naam))

    except Exception as e:
        conn.rollback()
        logger.error(f'Error processing HACCP checklist: {str(e)}')
        flash("Er is een fout opgetreden bij het verwerken van de checklist.", "danger")
    finally:
        cur.close()
        conn.close()

    return render_template('haccp/fill_checklist.html',
                         chef_naam=chef_naam,
                         checklist=checklist,
                         checkpunten=checkpunten)

@app.route('/dashboard/<chef_naam>/haccp/reports', methods=['GET', 'POST'])
def haccp_reports(chef_naam):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Haal alle checklists op voor het filter
        cur.execute("""
            SELECT * FROM haccp_checklists 
            WHERE chef_id = %s
        """, (session['chef_id'],))
        checklists = cur.fetchall()

        # Filter parameters met veilige defaults
        try:
            start_date = datetime.strptime(
                request.args.get('start_date', ''), 
                '%Y-%m-%d'
            ).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        try:
            end_date = datetime.strptime(
                request.args.get('end_date', ''), 
                '%Y-%m-%d'
            ).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            end_date = datetime.now().strftime('%Y-%m-%d')

        selected_checklist = request.args.get('checklist_id')

        # Query voor metingen
        query = """
            SELECT m.*, c.omschrijving, c.grenswaarde, cl.naam as checklist_naam
            FROM haccp_metingen m
            JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
            JOIN haccp_checklists cl ON c.checklist_id = cl.checklist_id
            WHERE m.chef_id = %s
            AND DATE(m.timestamp) BETWEEN %s AND %s
        """
        params = [session['chef_id'], start_date, end_date]

        if selected_checklist:
            query += " AND cl.checklist_id = %s"
            params.append(selected_checklist)

        query += " ORDER BY m.timestamp DESC"
        
        cur.execute(query, tuple(params))
        metingen = cur.fetchall()

        # Bereken statistieken met veilige type conversies
        if metingen:
            afwijkingen = 0
            for m in metingen:
                try:
                    waarde = float(m['waarde'] or 0)
                    grenswaarde = float(m['grenswaarde'] or 0)
                    if waarde > grenswaarde:
                        afwijkingen += 1
                except (ValueError, TypeError):
                    continue
            
            compliance = ((len(metingen) - afwijkingen) / len(metingen) * 100) if metingen else 100
        else:
            compliance = 100

        if request.args.get('export'):
            return export_haccp_report(metingen, start_date, end_date, compliance)

        return render_template('haccp/reports.html',
                             chef_naam=chef_naam,
                             checklists=checklists,
                             metingen=metingen,
                             start_date=start_date,
                             end_date=end_date,
                             selected_checklist=selected_checklist,
                             compliance=compliance)

    except Exception as e:
        logger.error(f'Error in HACCP reports: {str(e)}')
        flash("Er is een fout opgetreden bij het ophalen van de HACCP rapportage.", "danger")
        return redirect(url_for('haccp_dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

def export_haccp_report(metingen, start_date, end_date, compliance):
    doc = Document()
    doc.add_heading('HACCP Rapport', 0)
    
    # Voeg periode toe
    doc.add_paragraph(f'Periode: {start_date} t/m {end_date}')
    doc.add_paragraph(f'Compliance score: {compliance:.1f}%')

    # Maak tabel met metingen
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    
    # Headers
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Datum'
    header_cells[1].text = 'Checklist'
    header_cells[2].text = 'Controlepunt'
    header_cells[3].text = 'Waarde'
    header_cells[4].text = 'Status'
    header_cells[5].text = 'Actie'

    # Voeg metingen toe
    for meting in metingen:
        row_cells = table.add_row().cells
        row_cells[0].text = meting['timestamp'].strftime('%d-%m-%Y %H:%M')
        row_cells[1].text = meting['checklist_naam']
        row_cells[2].text = meting['omschrijving']
        row_cells[3].text = f"{meting['waarde']}"
        
        if float(meting['waarde']) <= float(meting['grenswaarde']):
            row_cells[4].text = '✓ OK'
        else:
            row_cells[4].text = '⚠ Afwijking'
        
    # Exporteer document
    # Exporteer document
    # Exporteer document
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'haccp_rapport_{start_date}_{end_date}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/dashboard/<chef_naam>/haccp/meting/<int:meting_id>/update', methods=['POST'])
def update_haccp_meting(chef_naam, meting_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        # Debug logging
        app.logger.info(f"Received update request for meting {meting_id}")
        app.logger.info(f"Form data: {request.form}")

        waarde = request.form.get('waarde')
        actie_ondernomen = request.form.get('actie_ondernomen')

        if waarde is None:
            return jsonify({'success': False, 'error': 'Waarde ontbreekt'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Controleer eerst of de meting bestaat en van deze chef is
            cursor.execute("""
                SELECT m.meting_id, c.grenswaarde 
                FROM haccp_metingen m
                JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
                WHERE m.meting_id = %s AND m.chef_id = %s
            """, (meting_id, session['chef_id']))
            
            meting = cursor.fetchone()
            if not meting:
                return jsonify({'success': False, 'error': 'Meting niet gevonden'}), 404

            try:
                waarde_float = float(waarde)
            except ValueError:
                return jsonify({'success': False, 'error': 'Ongeldige waarde'}), 400

            # Update de meting (zonder explicit updated_at)
            cursor.execute("""
                UPDATE haccp_metingen 
                SET waarde = %s, actie_ondernomen = %s
                WHERE meting_id = %s 
                AND chef_id = %s
            """, (waarde_float, actie_ondernomen, meting_id, session['chef_id']))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({'success': False, 'error': 'Geen wijzigingen aangebracht'}), 400
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Meting succesvol bijgewerkt'
            })

        except mysql.connector.Error as e:
            conn.rollback()
            app.logger.error(f'Database error: {str(e)}')
            return jsonify({'success': False, 'error': f'Database fout: {str(e)}'}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        app.logger.error(f'Error updating HACCP measurement: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/dashboard/<chef_naam>/haccp/checklist/<int:checklist_id>/delete', methods=['POST'])
def delete_haccp_checklist(chef_naam, checklist_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Controleer eerst of de checklist van deze chef is
        cur.execute("""
            SELECT chef_id FROM haccp_checklists 
            WHERE checklist_id = %s
        """, (checklist_id,))
        
        result = cur.fetchone()
        if not result or result[0] != session['chef_id']:
            return jsonify({'success': False, 'error': 'Checklist niet gevonden of geen toegang'}), 404

        # Verwijder eerst alle metingen van deze checklist
        cur.execute("""
            DELETE m FROM haccp_metingen m
            JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
            WHERE c.checklist_id = %s
        """, (checklist_id,))

        # Verwijder dan alle checkpunten
        cur.execute("""
            DELETE FROM haccp_checkpunten 
            WHERE checklist_id = %s
        """, (checklist_id,))

        # Verwijder tenslotte de checklist zelf
        cur.execute("""
            DELETE FROM haccp_checklists 
            WHERE checklist_id = %s AND chef_id = %s
        """, (checklist_id, session['chef_id']))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f'Error deleting HACCP checklist: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

# ...existing code...

@app.route('/dashboard/<chef_naam>/delete_account', methods=['POST'])
def delete_account(chef_naam):
    form = FlaskForm()  # Create a form instance for CSRF validation
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('profile', chef_naam=chef_naam))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    cur = conn.cursor()
    try:
        chef_id = session['chef_id']
        
        # Verwijder alle gegevens die aan de chef zijn gekoppeld
        cur.execute("DELETE FROM dish_ingredients WHERE dish_id IN (SELECT dish_id FROM dishes WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM dishes WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM ingredients WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM password_resets WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM haccp_metingen WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM haccp_checkpunten WHERE checklist_id IN (SELECT checklist_id FROM haccp_checklists WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM haccp_checklists WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM chefs WHERE chef_id = %s", (chef_id,))
        
        conn.commit()
        session.clear()
        flash("Je account is succesvol verwijderd.", "success")
        return redirect(url_for('home'))
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting account: {str(e)}")
        flash("Er is een fout opgetreden bij het verwijderen van je account.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

# ...existing code...

@app.route('/dashboard/<chef_naam>/profile', methods=['GET', 'POST'])
def profile(chef_naam):
    form = FlaskForm()  # Add CSRF validation
    if request.method == 'POST':
        if not form.validate_on_submit():
            flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
            return redirect(url_for('profile', chef_naam=chef_naam))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Haal gebruikersgegevens op
        cur.execute("SELECT * FROM chefs WHERE chef_id = %s", (session['chef_id'],))
        chef = cur.fetchone()
        
        if request.method == 'POST':
            if 'update_password' in request.form:
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                if not check_password_hash(chef['wachtwoord'], current_password):
                    flash("Huidig wachtwoord is onjuist.", "danger")
                elif new_password != confirm_password:
                    flash("Nieuwe wachtwoorden komen niet overeen.", "danger")
                else:
                    hashed_pw = generate_password_hash(new_password, method='pbkdf2:sha256')
                    cur.execute("""
                        UPDATE chefs 
                        SET wachtwoord = %s 
                        WHERE chef_id = %s
                    """, (hashed_pw, session['chef_id']))
                    conn.commit()
                    flash("Wachtwoord succesvol gewijzigd!", "success")
            
            elif 'update_email' in request.form:
                new_email = request.form.get('email')
                if new_email:
                    cur.execute("""
                        UPDATE chefs 
                        SET email = %s 
                        WHERE chef_id = %s
                    """, (new_email, session['chef_id']))
                    conn.commit()
                    flash("E-mailadres succesvol gewijzigd!", "success")
                    
    except Exception as e:
        conn.rollback()
        logger.error(f"Profile update error: {str(e)}")
        flash("Er is een fout opgetreden bij het bijwerken van je profiel.", "danger")
    finally:
        cur.close()
        conn.close()
        
    return render_template('profile.html', chef_naam=chef_naam, chef=chef, form=form)

# -----------------------------------------------------------
#  Terms and Conditions
# -----------------------------------------------------------
@app.route('/terms')
def terms():
    return render_template('terms.html', form=FlaskForm())

# -----------------------------------------------------------
#  Quickstart Guide
# -----------------------------------------------------------
@app.route('/quickstart/')
def quickstart_index():
    return render_template('quickstart.html', form=FlaskForm())

# Add alias for backward compatibility of 'quickstart' endpoint:
@app.route('/quickstart', endpoint='quickstart')
def quickstart_alias():
    return quickstart_index()

# -----------------------------------------------------------
# Static files route
# -----------------------------------------------------------
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                               'favicon.png',
                               mimetype='image/png')

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------
if __name__ == '__main__':
    application = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    application.run(host='0.0.0.0', port=port, debug=debug_mode)
