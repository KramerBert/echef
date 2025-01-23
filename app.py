import os
from flask import Flask, request, redirect, url_for, render_template, session, flash, send_file
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from docx import Document
import io

load_dotenv()  # Load the values from .env

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Needed for session management

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
#  Registreren
# -----------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        naam = request.form.get('naam')
        email = request.form.get('email')
        wachtwoord = request.form.get('wachtwoord')

        # Wachtwoord hashen
        hashed_pw = generate_password_hash(wachtwoord)

        # Opslaan in DB
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error.", "danger")
            return redirect(url_for('register'))

        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO chefs (naam, email, wachtwoord)
                VALUES (%s, %s, %s)
            """, (naam, email, hashed_pw))
            conn.commit()
            flash("Registratie succesvol! Log nu in.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij registreren: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# -----------------------------------------------------------
#  Inloggen
# -----------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        wachtwoord = request.form.get('wachtwoord')

        # Ophalen gebruiker
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error.", "danger")
            return redirect(url_for('login'))

        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM chefs WHERE email = %s", (email,))
        chef = cur.fetchone()
        cur.close()
        conn.close()

        if chef is not None:
            stored_hash = chef['wachtwoord']
            # Vergelijk wachtwoorden
            if check_password_hash(stored_hash, wachtwoord):
                # Inloggen geslaagd
                session['chef_id'] = chef['chef_id']
                session['chef_naam'] = chef['naam']
                flash("Succesvol ingelogd!", "success")
                return redirect(url_for('dashboard', chef_naam=chef['naam']))
            else:
                flash("Onjuist wachtwoord.", "danger")
        else:
            flash("Onbekend e-mailadres.", "danger")

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

    # Haal alleen de ingrediënten van de ingelogde chef op
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
                           ingredienten=alle_ingredienten)

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
        verkoopprijs = request.form.get('verkoopprijs')
        gerecht_categorie = request.form.get('gerecht_categorie')

        try:
            cur.execute("""
                INSERT INTO dishes (chef_id, naam, beschrijving, verkoopprijs, categorie)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['chef_id'], naam, beschrijving, verkoopprijs, gerecht_categorie))
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
    if request.method == 'POST' and 'ingredientForm' in request.form:
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
        SELECT di.*, i.naam AS ingredient_naam, i.eenheid
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
#  Verkoopprijs Bijwerken
# -----------------------------------------------------------
@app.route('/update_price/<int:dish_id>', methods=['POST'])
def update_price(dish_id):
    """
    Update the verkoopprijs of a dish.
    """
    if 'chef_id' not in session:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('login'))

    new_price = request.form.get('new_price')
    if not new_price:
        flash("Geen prijs opgegeven.", "danger")
        return redirect(url_for('all_dishes'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('all_dishes'))
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE dishes
            SET verkoopprijs = %s
            WHERE dish_id = %s
        """, (new_price, dish_id))
        conn.commit()
        flash("Verkoopprijs bijgewerkt!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij bijwerken verkoopprijs: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('all_dishes'))

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
    """, tuple(selected_dish_ids))
    selected_dishes = cur.fetchall()

    cur.close()
    conn.close()

    # Maak een Word-document aan
    doc = Document()
    doc.add_heading('Geselecteerde Gerechten', 0)

    for dish in selected_dishes:
        doc.add_heading(dish['naam'], level=1)
        doc.add_paragraph(f"Chef: {dish['chef_naam']}")
        doc.add_paragraph(f"Categorie: {dish['categorie']}")
        doc.add_paragraph(f"Verkoopprijs: {dish['verkoopprijs']}")
        doc.add_paragraph(f"Totaal ingredient-kostprijs: {dish['totaal_ingredient_prijs'] if dish['totaal_ingredient_prijs'] else 'n.v.t.'}")
        doc.add_paragraph(f"Beschrijving: {dish['beschrijving'] if dish['beschrijving'] else 'Geen beschrijving'}")
        doc.add_paragraph("\n")

    # Sla het document op in een in-memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='gerechten.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# -----------------------------------------------------------
# Start de server
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
