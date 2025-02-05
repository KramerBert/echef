from flask import render_template, redirect, url_for, flash, request, session, jsonify
from . import ai_blueprint
from .forms import RecipeGenerationForm
from .utils import parse_recipe
from anthropic import Anthropic
from flask_wtf.csrf import generate_csrf
from app import get_db_connection  # Voeg deze import toe
import os
import logging

# Initialize Anthropic client
anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

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
            - Naam van het gerecht
            - Beschrijving
            - Ingrediëntenlijst met hoeveelheden
            - Bereidingswijze in stappen
            - Geschatte bereidingstijd
            - Moeilijkheidsgraad (1-5)"""
            
            user_prompt = f"""
            Maak een recept voor: {form.prompt.data}
            Keuken: {form.cuisine.data}
            Dieetwensen: {form.dietary.data if form.dietary.data else 'Geen specifieke wensen'}
            """

            # Gebruik Claude's API
            message = anthropic.messages.create(
                model="claude-2.1",  # Goedkoper model
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Haal het gegenereerde recept op
            generated_recipe = message.content[0].text

            return render_template('ai/show_recipe.html',
                                recipe=generated_recipe,
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
        parsed = parse_recipe(recipe_text)

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database verbindingsfout'}), 500

        cur = conn.cursor()
        try:
            # Voeg het gerecht toe
            cur.execute("""
                INSERT INTO dishes (chef_id, naam, beschrijving, bereidingswijze, 
                                  is_ai_generated, original_prompt, generation_date)
                VALUES (%s, %s, %s, %s, TRUE, %s, NOW())
            """, (session['chef_id'], parsed['naam'], parsed['beschrijving'],
                 '\n'.join(parsed['bereidingswijze']), recipe_text))
            
            dish_id = cur.lastrowid

            # Voeg ingrediënten toe of maak nieuwe aan indien nodig
            for ingredient in parsed['ingredienten']:
                # Kijk of het ingrediënt al bestaat
                cur.execute("""
                    SELECT ingredient_id FROM ingredients 
                    WHERE chef_id = %s AND naam = %s AND eenheid = %s
                """, (session['chef_id'], ingredient['naam'], ingredient['eenheid']))
                
                result = cur.fetchone()
                if result:
                    ingredient_id = result[0]
                else:
                    # Maak nieuw ingrediënt aan
                    cur.execute("""
                        INSERT INTO ingredients (chef_id, naam, eenheid)
                        VALUES (%s, %s, %s)
                    """, (session['chef_id'], ingredient['naam'], ingredient['eenheid']))
                    ingredient_id = cur.lastrowid

                # Koppel ingrediënt aan gerecht
                cur.execute("""
                    INSERT INTO dish_ingredients (dish_id, ingredient_id, hoeveelheid)
                    VALUES (%s, %s, %s)
                """, (dish_id, ingredient_id, ingredient['hoeveelheid']))

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
