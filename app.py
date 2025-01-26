import os
from flask import Flask, request, redirect, url_for, render_template, session, flash, send_file
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

load_dotenv()  # Load the values from .env

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = os.getenv("SECRET_KEY")  # Needed for session management

# Configure session handling
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
)

# Configure debug mode properly
if app.debug:
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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

def get_db_connection():
    """
    Creates a new database connection using the details from .env
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

# -----------------------------------------------------------
#  Homepage (index)
# -----------------------------------------------------------
@app.route('/')
def home():
    """
    Toon de homepage, met bijvoorbeeld een link naar inloggen/registreren.
    """
    return render_template('home.html')  # Zorg voor een home.html template

# -----------------------------------------------------------
#  Over e-Chef
# -----------------------------------------------------------
@app.route('/about')
def about():
    return render_template('about.html')

# -----------------------------------------------------------
#  AVG Privacy Verklaring
# -----------------------------------------------------------
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# -----------------------------------------------------------
#  Registreren
# -----------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            naam = secure_filename(request.form['naam'])
            email = request.form['email']
            wachtwoord = request.form['wachtwoord']

            if not all([naam, email, wachtwoord]):
                flash("Vul alle velden in.", "danger")
                return render_template('register.html')

            hashed_pw = generate_password_hash(wachtwoord, method='pbkdf2:sha256')

            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO chefs (naam, email, wachtwoord)
                    VALUES (%s, %s, %s)
                """, (naam, email, hashed_pw))
                conn.commit()
                flash("Registratie succesvol! Log nu in.", "success")
                return redirect(url_for('login'))
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

    return render_template('register.html')

# -----------------------------------------------------------
#  Inloggen
# -----------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            wachtwoord = request.form['wachtwoord']

            if not email or not wachtwoord:
                flash("Vul alle velden in.", "danger")
                return render_template('login.html')

            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection error")

            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SELECT * FROM chefs WHERE email = %s", (email,))
                chef = cur.fetchone()
                
                if chef and check_password_hash(chef['wachtwoord'], wachtwoord):
                    session.clear()
                    session['chef_id'] = chef['chef_id']
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

    return render_template('login.html')

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
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Ongeldige sessie. Log opnieuw in.", "warning")
        return redirect(url_for('login'))

    # Eventueel stats/overzicht tonen
    return render_template('dashboard.html', chef_naam=chef_naam)

# -----------------------------------------------------------
#  Ingrediënten Beheren
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/ingredients', methods=['GET', 'POST'])
def manage_ingredients(chef_naam):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
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
                # Voeg hier chef_id toe, zodat het ingrediënt exclusief is voor de ingelogde chef
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

    # Haal alleen de ingrediënten van de ingelogde chef op
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

    cur.close()
    conn.close()

    return render_template('manage_ingredients.html',
                           chef_naam=chef_naam,
                           ingredienten=alle_ingredienten,
                           unieke_categorieen=unieke_categorieen,
                           filter_categorie=filter_categorie)

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
    csv_writer = csv.writer(csv_content)
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
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('manage_dishes', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    # Opslaan van nieuw gerecht
    if request.method == 'POST' and 'gerechtForm' in request.form:
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

    cur.close()
    conn.close()

    return render_template('manage_dishes.html',
                           chef_naam=chef_naam,
                           gerechten=alle_gerechten)

# -----------------------------------------------------------
#  Gerecht Bewerken (Ingrediënten toevoegen)
# -----------------------------------------------------------
@app.route('/dashboard/<chef_naam>/dishes/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(chef_naam, dish_id):
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

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

    cur.close()
    conn.close()

    return render_template(
        'edit_dish.html',
        chef_naam=chef_naam,
        gerecht=gerecht,
        alle_ingredienten=alle_ingredienten,
        gerecht_ingredienten=gerecht_ingredienten,
        totaal_ingredient_prijs=totaal_ingredient_prijs
    )

@app.route('/chef/<chef_naam>/dish/<int:dish_id>/ingredient/<int:ingredient_id>/update', methods=['POST'])
def update_dish_ingredient(chef_naam, dish_id, ingredient_id):
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

    # Haal alle gerechten op en bereken de totale ingredient-kostprijs
    cur.execute("""
        SELECT d.*, c.naam as chef_naam, 
               (SELECT SUM(di.prijs_totaal) 
                FROM dish_ingredients di 
                WHERE di.dish_id = d.dish_id) as totaal_ingredient_prijs
        FROM dishes d
        JOIN chefs c ON d.chef_id = c.chef_id
        ORDER BY d.dish_id DESC
    """)
    alle_gerechten = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('all_dishes.html', gerechten=alle_gerechten)

# -----------------------------------------------------------
#  Export Dishes to MS Word
# -----------------------------------------------------------
@app.route('/export_dishes', methods=['POST'])
def export_dishes():
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

    # Haal de geselecteerde gerechten op
    format_strings = ','.join(['%s'] * len(selected_dish_ids))
    cur.execute(f"""
        SELECT d.*, c.naam as chef_naam, 
               (SELECT SUM(di.prijs_totaal) 
                FROM dish_ingredients di 
                WHERE di.dish_id = d.dish_id) as totaal_ingredient_prijs
        FROM dishes d
        JOIN chefs c ON d.chef_id = c.chef_id
        WHERE d.dish_id IN ({format_strings})
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
    """, tuple(selected_dish_ids))
    selected_dishes = cur.fetchall()

    cur.close()
    conn.close()

    # Maak een Word-document aan
    doc = Document()
    doc.add_heading('Menukaart', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Voeg veiligheidscontroles toe voor alle velden
    for dish in selected_dishes:
        verkoopprijs = dish['verkoopprijs'] if dish['verkoopprijs'] else 'n.v.t.'
        naam = dish['naam'] if dish['naam'] else 'Onbekend gerecht'
        heading = doc.add_heading(f"{naam} - €{verkoopprijs}", level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        description_text = dish['beschrijving'] if dish['beschrijving'] else 'Geen beschrijving'
        description = doc.add_paragraph(description_text)
        description.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph("\n").alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Sla het document op in een in-memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    safe_filename = quote('Menukaart.docx', safe='')
    return send_file(
        buffer, 
        as_attachment=True, 
        download_name=safe_filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

# -----------------------------------------------------------
#  Export Cookbook to MS Word
# -----------------------------------------------------------
@app.route('/export_cookbook', methods=['POST'])
def export_cookbook():
    """
    Export all dishes to a Microsoft Word document as a cookbook.
    """
    if 'chef_id' not in session:
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

    return render_template('edit_ingredient.html', chef_naam=chef_naam, ingredient=ingredient)

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
    if 'chef_id' not in session:
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
    return render_template('instructions.html')

# -----------------------------------------------------------
# Voeg error handler toe voor Werkzeug exceptions
@app.errorhandler(HTTPException)
def handle_exception(e):
    return render_template('error.html', error=e), e.code

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
