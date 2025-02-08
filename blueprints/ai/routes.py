from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from bs4 import BeautifulSoup
from anthropic import Anthropic
from .utils import parse_recipe
from .forms import RecipeGenerationForm
from app import get_db_connection  # Voeg deze import toe
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Anthropic client
api_key = os.getenv('ANTHROPIC_API_KEY')
logging.debug(f"Anthropic API Key: {api_key}")  # Log the API key
anthropic = Anthropic(api_key=api_key)

ai_blueprint = Blueprint('ai', __name__, url_prefix='/ai')

@ai_blueprint.route('/generate', methods=['GET', 'POST'])
def generate_recipe():
    """Genereer een recept met behulp van de AI."""
    if 'chef_id' not in session:
        flash("Je moet ingelogd zijn om een recept te genereren.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        gerecht_naam = request.form.get('gerecht_naam')
        
        client = Anthropic()
        prompt = f"""
        Genereer een recept voor een gerecht genaamd {gerecht_naam}.
        Geef een korte beschrijving, een lijst met ingrediënten (inclusief hoeveelheden en eenheden), en een stapsgewijze bereidingswijze.
        
        Gebruik de volgende structuur:
        
        Naam: [Naam van het gerecht]
        Beschrijving: [Korte beschrijving]
        
        Ingrediënten:
        - [Hoeveelheid] [Eenheid] [Ingrediënt]
        - ...
        
        Bereidingswijze:
        1. [Stap 1]
        2. [Stap 2]
        ...
        """
        
        try:
            message = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            recipe_text = message.content[0].text
            recipe = parse_recipe(recipe_text)
            return render_template('ai/show_recipe.html', recipe=recipe)
        except Exception as e:
            flash(f"Fout bij genereren recept: {str(e)}", "danger")
            return render_template('ai/generate_recipe.html')

    return render_template('ai/generate_recipe.html')

@ai_blueprint.route('/save_recipe', methods=['POST'])
def save_recipe():
    """Slaat het gegenereerde recept op in de database."""
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Niet ingelogd'}), 403

    recipe_text = request.json.get('recipe_text')
    if not recipe_text:
        return jsonify({'success': False, 'error': 'Geen recept tekst ontvangen'}), 400

    # Database connectie
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500

    cur = conn.cursor()
    try:
        # Extract recipe details from the text
        recipe = parse_recipe(recipe_text)
        
        # Insert the dish into the database
        cur.execute("""
            INSERT INTO dishes (chef_id, naam, beschrijving, bereidingswijze)
            VALUES (%s, %s, %s, %s)
        """, (session['chef_id'], recipe['naam'], recipe['beschrijving'], '\n'.join(recipe['bereidingswijze'])))
        dish_id = cur.lastrowid
        
        # Insert the ingredients into the database
        for ingredient in recipe['ingredienten']:
            cur.execute("""
                INSERT INTO ingredients (chef_id, naam, eenheid, prijs_per_eenheid)
                VALUES (%s, %s, %s, %s)
            """, (session['chef_id'], ingredient['naam'], ingredient.get('eenheid', ''), 0.0))  # Default price is 0
            ingredient_id = cur.lastrowid
            
            # Link the ingredient to the dish
            cur.execute("""
                INSERT INTO dish_ingredients (dish_id, ingredient_id, hoeveelheid, prijs_totaal)
                VALUES (%s, %s, %s, %s)
            """, (dish_id, ingredient_id, ingredient.get('hoeveelheid', 0), 0.0))  # Default quantity and price

        conn.commit()
        return jsonify({'success': True, 'message': 'Recept succesvol opgeslagen', 'dish_id': dish_id})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return render_template('ai/generate_recipe.html')