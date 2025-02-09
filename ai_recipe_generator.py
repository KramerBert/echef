import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from anthropic import Anthropic
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging
from flask_wtf import FlaskForm
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Update to explicitly check for ANTHROPIC_API_KEY
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY not found in environment variables!")
    logger.debug("Available environment variables: " + ", ".join(os.environ.keys()))

# Blueprint Configuration
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# Database configuration
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Database configuration
DB_CONFIG = {
    'host': DB_HOST,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'port': DB_PORT
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

# Route to display the AI recipe generation form
@ai_bp.route('/generate_recipe', methods=['GET', 'POST'])
def generate_recipe():
    form = FlaskForm()
    if 'chef_id' not in session:
        flash("Je moet ingelogd zijn om een recept te genereren.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        if not form.validate_on_submit():
            flash("Ongeldige CSRF-token.", "danger")
            return render_template('ai/generate_recipe.html', form=form)
            
        prompt = request.form.get('prompt')
        if not prompt:
            flash("Prompt mag niet leeg zijn.", "danger")
            return render_template('ai/generate_recipe.html', form=form)

        try:
            # Check if Anthropic API key is set
            if not ANTHROPIC_API_KEY:
                flash("Anthropic API key is not set. Please configure it.", "danger")
                return render_template('ai/generate_recipe.html', form=form)

            # Initialize Anthropic client
            client = Anthropic(api_key=ANTHROPIC_API_KEY)

            # Create the message with improved prompt
            message = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"""Genereer een recept in het Nederlands, gebaseerd op het volgende verzoek: {prompt}
                    Gebruik het volgende formaat:
                    TITLE: [Naam van het Gerecht]
                    
                    DESCRIPTION: [Korte beschrijving]
                    
                    INGREDIENTS:
                    - [ingrediënt 1]
                    - [ingrediënt 2]
                    
                    INSTRUCTIONS:
                    1. [stap 1]
                    2. [stap 2]
                    
                    NOTES: [Optionele tips of opmerkingen]
                    
                    Zorg ervoor dat alle tekst in het Nederlands is."""
                }]
            )

            # Extract and format the generated recipe
            raw_recipe = message.content[0].text
            generated_recipe = raw_recipe.replace('<br>', '\n')

            # Store the recipe in the session for later use
            session['pending_recipe'] = {
                'recipe': generated_recipe,
                'prompt': prompt
            }

            return render_template('ai/preview_recipe.html', recipe=generated_recipe, form=form)

        except Exception as e:
            logger.error(f"Error generating recipe: {str(e)}")
            flash(f"Fout bij genereren recept: {str(e)}", "danger")
            return render_template('ai/generate_recipe.html', form=form)

    return render_template('ai/generate_recipe.html', form=form)

@ai_bp.route('/save_recipe', methods=['POST'])
def save_recipe():
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token.", "danger")
        return redirect(url_for('ai.generate_recipe'))

    if 'pending_recipe' not in session:
        flash("Geen recept gevonden om op te slaan.", "danger")
        return redirect(url_for('generate_recipe'))

    try:
        generated_recipe = session['pending_recipe']['recipe']
        prompt = session['pending_recipe']['prompt']

        # Split the recipe into sections
        sections = generated_recipe.split('\n\n')
        
        # Extract each section
        title = next((s.replace('TITLE:', '').strip() for s in sections if s.startswith('TITLE:')), 'AI Generated Recipe')
        description = next((s.replace('DESCRIPTION:', '').strip() for s in sections if s.startswith('DESCRIPTION:')), 'Generated by AI')
        ingredients = next((s.replace('INGREDIENTS:', '').strip() for s in sections if s.startswith('INGREDIENTS:')), '')
        instructions = next((s.replace('INSTRUCTIONS:', '').strip() for s in sections if s.startswith('INSTRUCTIONS:')), '')
        notes = next((s.replace('NOTES:', '').strip() for s in sections if s.startswith('NOTES:')), '')

        # Format ingredients and instructions for storage
        formatted_ingredients = ingredients
        formatted_instructions = instructions

        # Combine method sections with proper formatting
        method = f"INGREDIENTEN:\n{formatted_ingredients}\n\nBEREIDINGSWIJZE:\n{formatted_instructions}"
        if notes:
            method += f"\n\nOPMERKINGEN:\n{notes}"

        # Store in database
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error.", "danger")
            return redirect(url_for('generate_recipe'))
        
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO dishes (chef_id, naam, beschrijving, ingredienten, bereidingswijze, is_ai_generated, original_prompt, generation_date, ai_model)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['chef_id'], title, description, formatted_ingredients, formatted_instructions, 1, prompt, datetime.now(), "claude-3-opus-20240229"))
            conn.commit()
            flash("Recept succesvol opgeslagen!", "success")
            
            # Clear the pending recipe from session
            session.pop('pending_recipe', None)
            
            return redirect(url_for('all_dishes'))
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij opslaan recept: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        flash(f"Fout bij opslaan recept: {str(e)}", "danger")

    return redirect(url_for('generate_recipe'))
