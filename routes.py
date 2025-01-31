from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .database import (get_db_cursor, PREPARED_STATEMENTS, Error, 
                      get_cached_ingredients, execute_bulk_operation, BULK_STATEMENTS)
import time
from datetime import datetime
from .models import db, Gerecht, Ingredient, GerechtIngredient
from .app import app, get_db_connection  # Import app en get_db_connection om de configuratie te gebruiken
import smtplib  # Import smtplib voor het verzenden van e-mails
from email.mime.text import MIMEText  # Import MIMEText voor e-mailinhoud
from email.mime.multipart import MIMEMultipart  # Import MIMEMultipart voor e-mailinhoud
from werkzeug.security import generate_password_hash  # Import generate_password_hash voor wachtwoord hashing
import os  # Import os voor toegang tot omgevingsvariabelen

# Ensure get_db_connection is correctly imported
from .app import get_db_connection

# Blueprint maken
routes = Blueprint('routes', __name__)

@routes.route('/', methods=['GET'])
def index():
    return "Welcome to eChef!"

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
        app.logger.error(f"Email error: {str(e)}")
        return False

# Verwijder de reset_password route uit de Blueprint
# @routes.route('/reset-password/<token>', methods=['GET', 'POST'])
# def reset_password(token):
#     # ...existing code...
