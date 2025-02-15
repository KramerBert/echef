import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer
from flask import url_for, current_app
from werkzeug.security import generate_password_hash

def generate_confirmation_token(email):
    """Generate email confirmation token"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    """Verify email confirmation token."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
        return email
    except Exception as e:
        current_app.logger.error(f"Token confirmation failed: {str(e)}")
        return False

def send_confirmation_email(email, token):
    """Send confirmation email"""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = email
    msg['Subject'] = "e-Chef Email Verificatie"
    
    scheme = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    verify_url = url_for('auth.verify_email', token=token, _external=True, _scheme=scheme)
    
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

def send_reset_email(email, token):
    """Stuur een wachtwoord reset email."""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = email
    msg['Subject'] = "e-Chef Wachtwoord Reset"
    
    # Gebruik HTTPS in productie en HTTP in lokale ontwikkeling
    scheme = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    reset_url = url_for('auth.reset_password', token=token, _external=True, _scheme=scheme)
    
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

def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256')
