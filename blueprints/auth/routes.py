import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import current_app
from .utils import generate_confirmation_token, confirm_token, send_confirmation_email, send_reset_email, hash_password
from utils.db import get_db_connection

bp = Blueprint('auth', __name__, template_folder='templates')

# Forms
class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField('Inloggen')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nieuw wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig wachtwoord', 
                                    validators=[DataRequired(), 
                                                EqualTo('password', message='Wachtwoorden moeten overeenkomen')])
    submit = SubmitField('Wachtwoord wijzigen')

class ForgotPasswordForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    recaptcha = RecaptchaField()
    submit = SubmitField('Reset Link Versturen')

class RegisterForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig Wachtwoord', 
                                    validators=[DataRequired(), 
                                                EqualTo('wachtwoord', message='Wachtwoorden moeten overeenkomen')])
    terms = BooleanField('Ik ga akkoord met de algemene voorwaarden en privacy policy', validators=[InputRequired(message='Je moet akkoord gaan met de algemene voorwaarden en privacy policy')])
    recaptcha = RecaptchaField()
    submit = SubmitField('Registreer')

# Routes
@bp.route('/register', methods=['GET', 'POST'])
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
                return render_template('auth/register.html', form=form)

            hashed_pw = hash_password(wachtwoord)

            conn = current_app.get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor()
            try:
                # Add email_verified column with default value 0
                cur.execute("""
                    INSERT INTO chefs (naam, email, wachtwoord, email_verified, terms_accepted, privacy_accepted)
                    VALUES (%s, %s, %s, 0, %s, %s)
                """, (naam, email, hashed_pw, datetime.utcnow(), datetime.utcnow()))
                conn.commit()

                # Generate confirmation token and send email
                token = generate_confirmation_token(email)
                if send_confirmation_email(email, token):
                    flash("Registratie succesvol! Check je email om je account te verifiëren.", "success")
                    return redirect(url_for('auth.verify_email'))  # Zonder token parameter
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

    return render_template('auth/register.html', form=form)

@bp.route('/verify-email', methods=['GET'])
@bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token=None):
    """Handle both the initial verification page and token verification"""
    if not token:
        # Show the initial verification page
        return render_template('auth/verify_email.html', verified=False)
    
    # Handle token verification
    email = confirm_token(token)
    if email:
        conn = current_app.get_db_connection()
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
                return render_template('auth/verify_email.html', verified=True)
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f'Email verification error: {str(e)}')
                flash("Er is een fout opgetreden bij het verifiëren van je email.", "danger")
            finally:
                cur.close()
                conn.close()
    else:
        flash("Ongeldige of verlopen verificatie link.", "danger")
    
    return render_template('auth/verify_email.html', verified=False)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            email = form.email.data
            wachtwoord = form.wachtwoord.data

            conn = get_db_connection()  # Use the imported function
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SELECT * FROM chefs WHERE email = %s", (email,))
                chef = cur.fetchone()
                
                # Check for unsupported scrypt hash and advise password reset
                if chef and chef.get('wachtwoord','').startswith("scrypt:"):
                    flash("Je account maakt gebruik van een wachtwoord hash (scrypt) die niet langer ondersteund wordt. Reset je wachtwoord.", "danger")
                    return redirect(url_for('auth.forgot_password'))
                
                if chef and check_password_hash(chef['wachtwoord'], wachtwoord):
                    if not chef.get('email_verified', False):
                        flash("Verifieer eerst je email adres voordat je inlogt.", "warning")
                        return redirect(url_for('auth.verify_email'))
                    
                    session.clear()
                    chef_id = chef.get('chef_id')
                    if chef_id is None:
                        flash("Er is een fout opgetreden bij het inloggen: ongeldige accountgegevens.", "danger")
                        return redirect(url_for('auth.login'))
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
            current_app.logger.error(f'Login error: {str(e)}')
            flash("Er is een fout opgetreden bij inloggen.", "danger")

    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    session.clear()
    flash("Je bent uitgelogd.", "info")
    return redirect(url_for('home'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        # Controleer of er daadwerkelijk een e-mail is ingevuld
        if not email:
            flash("Voer een geldig e-mailadres in.", "danger")
            return redirect(url_for('auth.forgot_password'))
        
        conn = current_app.get_db_connection()
        if conn is None:
            flash("Databaseverbinding mislukt.", "danger")
            return redirect(url_for('auth.forgot_password'))
        
        cur = conn.cursor(dictionary=True)
        try:
            # Controleer of het e-mailadres bestaat in de database
            cur.execute("SELECT chef_id FROM chefs WHERE email = %s", (email,))
            chef = cur.fetchone()
            if chef is None:
                flash("E-mailadres niet gevonden.", "danger")
                return redirect(url_for('auth.forgot_password'))
            
            # Genereer reset token en stuur reset e-mail
            token = generate_confirmation_token(email)
            if send_reset_email(email, token):
                flash("Een reset link is naar je e-mailadres gestuurd.", "info")
            else:
                flash("Er is een fout opgetreden bij het versturen van de e-mail.", "danger")
        except Exception as e:
            current_app.logger.error(f"Error in forgot_password: {str(e)}")
            flash("Er is een fout opgetreden.", "danger")
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    current_app.logger.debug(f"Received reset token: {token}")
    if not token or not isinstance(token, str) or len(token) > 128:
        flash("Ongeldige reset link.", "danger")
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm()
    email = confirm_token(token)
    if not email:
        flash("Reset token is ongeldig of verlopen.", "danger")
        current_app.logger.error(f"Reset token invalid or expired for token: {token}")
        return redirect(url_for('auth.login'))
    conn = current_app.get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('auth.login'))
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT chef_id FROM chefs WHERE email = %s", (email,))
    chef = cur.fetchone()
    if chef is None:
        flash("E-mailadres niet gevonden.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for('auth.login'))
    if form.validate_on_submit():
        new_password = form.password.data
        cur.execute("UPDATE chefs SET wachtwoord = %s WHERE chef_id = %s",
                    (hash_password(new_password), chef['chef_id']))
        conn.commit()
        flash("Je wachtwoord is succesvol gewijzigd!", "success")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, token=token)
