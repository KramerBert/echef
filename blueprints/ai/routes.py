from flask import render_template, redirect, url_for, flash, request, session, jsonify
from . import ai_blueprint
from .forms import RecipeGenerationForm
from .utils import parse_recipe
from anthropic import Anthropic
from flask_wtf.csrf import generate_csrf
from app import get_db_connection  # Voeg deze import toe
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Anthropic client
api_key = os.getenv('ANTHROPIC_API_KEY')
logging.debug(f"Anthropic API Key: {api_key}")  # Log the API key
anthropic = Anthropic(api_key=api_key)

@ai_blueprint.route('/generate', methods=['GET', 'POST'])
def generate_recipe():
    if 'chef_id' not in session:
        flash("Log eerst in om AI-recepten te genereren.", "warning")
        return redirect(url_for('login'))

    form = RecipeGenerationForm()
    if form.validate_on_submit():
        try:
            # Bouw de prompt op
            system_prompt = """Je bent een ervaren chef-kok die helpt bij het maken van recepten.
            Geef het recept in het volgende format:

            Naam van het gerecht: [Naam van het gerecht] (maximaal 50 tekens)
            Beschrijving: [Een korte beschrijving van het gerecht] (maximaal 150 tekens)

            Ingrediënten:
            - [Hoeveelheid] [Eenheid] [Naam van het ingrediënt]
            - ...

            Bereidingswijze:
            1. [Stap 1]
            2. [Stap 2]
            ...
            """
            user_prompt = f"""
            Maak een recept voor: {form.prompt.data}
            Keuken: {form.cuisine.data}
            Dieetwensen: {form.dietary.data if form.dietary.data else 'Geen specifieke wensen'}
            """
            # Gebruik Claude's API
            message = anthropic.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Haal het gegenereerde recept op
            generated_recipe = message.content[0].text
            parsed_recipe = parse_recipe(generated_recipe)

            return render_template('ai/show_recipe.html',
                                   recipe=parsed_recipe,
                                   form=form)
        except Exception as e:
            flash(f"Er is een fout opgetreden: {str(e)}", "danger")
            return render_template('ai/generate_recipe.html', form=form)

    return render_template('ai/generate_recipe.html', form=form)

@ai_blueprint.route('/save_recipe', methods=['POST'])
def save_recipe():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Niet ingelogd'}), 403
    try:
        data = request.json
        recipe_text = data.get('recipe_text')
        logging.debug(f"Received recipe_text: {recipe_text}")  # Log the received recipe_text
        parsed = parse_recipe(recipe_text)
        logging.debug(f"Parsed recipe: {parsed}")  # Log the parsed recipe

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database verbindingsfout'}), 500

        cur = conn.cursor()
        try:
            # Combineer ingrediënten en bereidingswijze tot één string
            ingredienten_string = "\nIngrediënten:\n"
            if parsed['ingredienten']:
                for ingredient in parsed['ingredienten']:
                    hoeveelheid = ingredient['hoeveelheid'] if ingredient['hoeveelheid'] else ""
                    eenheid = ingredient['eenheid'] if ingredient['eenheid'] else ""
                    ingredienten_string += f"- {hoeveelheid} {eenheid} {ingredient['naam']}\n"
            else:
                ingredienten_string += "Geen ingrediënten gevonden.\n"

            bereidingswijze_string = "\nBereidingswijze:\n"
            if parsed['bereidingswijze']:
                for i, stap in enumerate(parsed['bereidingswijze']):
                     bereidingswijze_string += f"{i+1}. {stap}\n"
            else:
                bereidingswijze_string += "Geen bereidingswijze gevonden.\n"

            volledige_bereidingswijze = ingredienten_string + bereidingswijze_string

            cur.execute("""
                INSERT INTO dishes (chef_id, naam, beschrijving, bereidingswijze, 
                                  is_ai_generated, original_prompt, generation_date)
                VALUES (%s, %s, %s, %s, TRUE, %s, NOW())
            """, (session['chef_id'], parsed['naam'], parsed['beschrijving'],
                 volledige_bereidingswijze, recipe_text))
            dish_id = cur.lastrowid

            conn.commit()
            return jsonify({
                'success': True,
                'dish_id': dish_id,
                'message': 'Recept succesvol opgeslagen!'
            })

        except Exception as e:
            conn.rollback()
            logging.error(f'Error saving AI recipe: {str(e)}')
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logging.error(f'Error in save_recipe: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500