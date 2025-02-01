from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from .database import (get_db_cursor, PREPARED_STATEMENTS, Error, 
                      get_cached_ingredients, execute_bulk_operation, BULK_STATEMENTS)
import time
from datetime import datetime
from .models import db, Gerecht, Ingredient, GerechtIngredient
import smtplib  # Import smtplib voor het verzenden van e-mails
from email.mime.text import MIMEText  # Import MIMEText voor e-mailinhoud
from email.mime.multipart import MIMEMultipart  # Import MIMEMultipart voor e-mailinhoud
from werkzeug.security import generate_password_hash  # Import generate_password_hash voor wachtwoord hashing
from werkzeug.utils import secure_filename  # Import secure_filename voor veilige bestandsnamen
import os  # Import os voor toegang tot omgevingsvariabelen
from .forms import RegisterForm, LoginForm, NewForm  # Ensure forms are imported
import requests  # Import the requests module
from itsdangerous import URLSafeTimedSerializer  # Import URLSafeTimedSerializer for token generation

# Ensure get_db_connection is correctly imported
from .database import get_db_connection

# Blueprint maken
routes = Blueprint('routes', __name__)

def generate_confirmation_token(email):
    """Generate email confirmation token"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def send_confirmation_email(email, token):
    """Send confirmation email"""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
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
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        current_app.logger.error(f"Email error: {str(e)}")
        return False

@routes.route('/', methods=['GET'])
def index():
    try:
        current_app.logger.info('Accessing index route')
        return "Welcome to eChef!"
    except Exception as e:
        current_app.logger.error(f'Error in index route: {str(e)}')
        return "An error occurred", 500

@routes.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    # Process the data...
    return jsonify({"message": "Data received", "data": data})

@routes.route('/manage_dishes/<chef_naam>', methods=['GET', 'POST'])
def manage_dishes(chef_naam):
    if request.method == 'POST':
        if 'gerechtForm' in request.form:
            naam = request.form.get('naam')
            beschrijving = request.form.get('beschrijving')
            categorie = request.form.get('gerecht_categorie')
            bereidingswijze = request.form.get('bereidingswijze')
            # TODO: Implementeer database opslag
            flash('Nieuw gerecht toegevoegd!', 'success')
            return redirect(url_for('routes.manage_dishes', chef_naam=chef_naam))
    return render_template('manage_dishes.html', chef_naam=chef_naam)

@routes.route('/edit_dish/<chef_naam>/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(chef_naam, dish_id):
    try:
        with get_db_cursor() as cursor:
            # Gebruik gecachede ingrediënten (ververst elke 5 minuten)
            cache_timestamp = int(time.time() / 300)  # 5 minuten cache
            alle_ingredienten = get_cached_ingredients(cache_timestamp)
            
            # Rest van de queries blijven real-time
            cursor.execute(PREPARED_STATEMENTS['get_gerecht'], (dish_id,))
            gerecht = cursor.fetchone()
            
            if not gerecht:
                return render_template('error.html', 
                                    error={'code': 404, 
                                          'description': 'Gerecht niet gevonden'})
            
            # Haal gerecht ingrediënten op
            cursor.execute(PREPARED_STATEMENTS['get_gerecht_ingredienten'], (dish_id,))
            gerecht_ingredienten = cursor.fetchall()

            if request.method == 'POST':
                if 'updateForm' in request.form:
                    cursor.execute(PREPARED_STATEMENTS['update_gerecht'], (
                        request.form.get('naam'),
                        request.form.get('beschrijving'),
                        request.form.get('gerecht_categorie'),
                        request.form.get('bereidingswijze'),
                        dish_id
                    ))
                    flash('Gerecht bijgewerkt!', 'success')
                
                elif 'ingredientForm' in request.form:
                    cursor.execute(PREPARED_STATEMENTS['add_ingredient'], (
                        dish_id,
                        request.form.get('ingredient_id'),
                        float(request.form.get('hoeveelheid'))
                    ))
                    flash('Ingredient toegevoegd!', 'success')

            return render_template('edit_dish.html',
                                chef_naam=chef_naam,
                                gerecht=gerecht,
                                alle_ingredienten=alle_ingredienten,
                                gerecht_ingredienten=gerecht_ingredienten)

    except Error as e:
        return render_template('error.html', 
                            error={'code': 500, 
                                  'description': f'Database error: {str(e)}'})

@routes.route('/update_dish_ingredient/<chef_naam>/<int:dish_id>/<int:ingredient_id>', methods=['POST'])
def update_dish_ingredient(chef_naam, dish_id, ingredient_id):
    # TODO: Implementeer ingredient hoeveelheid update
    return redirect(url_for('routes.edit_dish', chef_naam=chef_naam, dish_id=dish_id))

@routes.route('/remove_dish_ingredient/<chef_naam>/<int:dish_id>/<int:ingredient_id>', methods=['POST'])
def remove_dish_ingredient(chef_naam, dish_id, ingredient_id):
    # TODO: Implementeer ingredient verwijderen
    return redirect(url_for('routes.edit_dish', chef_naam=chef_naam, dish_id=dish_id))

@routes.route('/edit_ingredient/<chef_naam>/<int:ingredient_id>')
def edit_ingredient(chef_naam, ingredient_id):
    # TODO: Implementeer ingredient bewerken
    return render_template('edit_ingredient.html', chef_naam=chef_naam, ingredient_id=ingredient_id)

@routes.route('/all_dishes')
def all_dishes():
    # TODO: Implementeer overzicht van alle gerechten
    return render_template('all_dishes.html')

@routes.route('/bulk_update_ingredients/<chef_naam>/<int:dish_id>', methods=['POST'])
def bulk_update_ingredients(chef_naam, dish_id):
    """Nieuwe route voor bulk updates"""
    try:
        updates = request.json.get('updates', [])
        if updates:
            data = [(amount, dish_id, ing_id) for ing_id, amount in updates]
            execute_bulk_operation(BULK_STATEMENTS['update_ingredients_bulk'], data)
            flash('Alle ingrediënten bijgewerkt!', 'success')
        return redirect(url_for('routes.edit_dish', chef_naam=chef_naam, dish_id=dish_id))
    except Error as e:
        return render_template('error.html', 
                            error={'code': 500, 
                                  'description': f'Bulk update failed: {str(e)}'})

def send_reset_email(email, token):
    """Stuur een wachtwoord reset email."""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = email
    msg['Subject'] = "e-Chef Wachtwoord Reset"
    
    # Gebruik HTTPS in productie en HTTP in lokale ontwikkeling
    scheme = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    reset_url = url_for('reset_password', token=token, _external=True, _scheme=scheme)
    
    body = f"""
    Er is een wachtwoord reset aangevraagd voor je e-Chef account.
    Klik op de onderstaande link om je wachtwoord te resetten:
    
    {reset_url}
    
    Deze link verloopt over {current_app.config['RESET_TOKEN_EXPIRE_MINUTES']} minuten.
    Als je geen reset hebt aangevraagd, kun je deze email negeren.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        current_app.logger.error(f"Email error: {str(e)}")
        return False

def verify_recaptcha(response):
    """Verify the reCAPTCHA response"""
    verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    payload = {
        'secret': current_app.config['RECAPTCHA_SECRET_KEY'],
        'response': response
    }
    try:
        response = requests.post(verify_url, data=payload)
        result = response.json()
        current_app.logger.info(f"reCAPTCHA verification result: {result}")
        return result.get('success', False)
    except Exception as e:
        current_app.logger.error(f"reCAPTCHA verification error: {str(e)}")
        return False

@routes.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            naam = secure_filename(form.naam.data)
            email = form.email.data
            wachtwoord = form.wachtwoord.data
            recaptcha_response = request.form.get('g-recaptcha-response')

            if not recaptcha_response:
                flash("Vul de reCAPTCHA in.", "danger")
                return render_template('register.html', form=form, recaptcha_site_key=current_app.config.get('RECAPTCHA_SITE_KEY'))

            # Verify reCAPTCHA
            if not verify_recaptcha(recaptcha_response):
                flash("reCAPTCHA verificatie mislukt. Probeer opnieuw.", "danger")
                return render_template('register.html', form=form, recaptcha_site_key=current_app.config.get('RECAPTCHA_SITE_KEY'))

            hashed_pw = generate_password_hash(wachtwoord, method='pbkdf2:sha256')

            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO chefs (naam, email, wachtwoord, email_verified)
                    VALUES (%s, %s, %s, 0)
                """, (naam, email, hashed_pw))
                conn.commit()

                # Generate confirmation token and send email
                token = generate_confirmation_token(email)
                if send_confirmation_email(email, token):
                    flash("Registratie succesvol! Check je email om je account te verifiëren.", "success")
                    return redirect(url_for('verify_email'))
                else:
                    flash("Registratie succesvol, maar er ging iets mis met het versturen van de verificatie email. Neem contact op met support.", "warning")

            except Exception as e:
                conn.rollback()
                current_app.logger.error(f'Registration error: {str(e)}')
                flash("Er is een fout opgetreden bij registratie.", "danger")
            finally:
                cur.close()
                conn.close()

        except Exception as e:
            current_app.logger.error(f'Registration error: {str(e)}')
            flash("Er is een fout opgetreden.", "danger")

    return render_template('register.html', form=form, recaptcha_site_key=current_app.config.get('RECAPTCHA_SITE_KEY'))

@routes.route('/specific_route', methods=['GET', 'POST'])
def specific_route():
    form = NewForm()
    if form.validate_on_submit():
        # Process form data
        field1 = form.field1.data
        field2 = form.field2.data
        # ... do something with the data ...
        flash('Form submitted successfully!', 'success')
        return redirect(url_for('specific_route'))
    return render_template('specific_template.html', form=form)

# Verwijder de reset_password route uit de Blueprint
# @routes.route('/reset-password/<token>', methods=['GET', 'POST'])
# def reset_password(token):
#     # ...existing code...
