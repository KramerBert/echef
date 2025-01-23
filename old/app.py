from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser

# Laad omgevingsvariabelen uit .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("The SECRET_KEY environment variable is not set. Please set it in the .env file.")

# Databaseconfiguratie uit .env
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB"),
    "port": int(os.getenv("MYSQL_PORT"))
}

# Emailconfiguratie uit .env
email_config = {
    "smtp_server": os.getenv("SMTP_SERVER"),
    "smtp_port": os.getenv("SMTP_PORT"),
    "smtp_user": os.getenv("SMTP_USER"),
    "smtp_password": os.getenv("SMTP_PASSWORD"),
    "from_email": os.getenv("FROM_EMAIL")
}

# Test databaseverbinding
try:
    connection = mysql.connector.connect(**db_config)
    if connection.is_connected():
        print("Succesvol verbonden met MySQL!")
except Error as e:
    print("Fout bij verbinden met MySQL:", e)

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = email_config['from_email']
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        server.starttls()
        server.login(email_config['smtp_user'], email_config['smtp_password'])
        text = msg.as_string()
        server.sendmail(email_config['from_email'], to_email, text)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print("Failed to send email:", e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chefs", methods=["GET"])
def get_chefs():
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM chefs")
    chefs = cursor.fetchall()
    return jsonify(chefs)

@app.route("/chefs", methods=["POST"])
def add_chef():
    data = request.get_json()
    cursor = connection.cursor()
    query = "INSERT INTO chefs (name, email, telefoonnummer) VALUES (%s, %s, %s)"
    values = (data['name'], data['email'], data['telefoonnummer'])
    cursor.execute(query, values)
    connection.commit()
    return jsonify({"message": "Chef added successfully"}), 201

@app.route("/aanmelden", methods=["GET"])
def aanmelden_form():
    return render_template("aanmelden.html")

@app.route("/aanmelden", methods=["POST"])
def aanmelden():
    data = request.get_json()
    cursor = connection.cursor()
    hashed_password = generate_password_hash(data['password'])
    query = "INSERT INTO chefs (name, email, telefoonnummer, password) VALUES (%s, %s, %s, %s)"
    values = (data['name'], data['email'], data['telefoonnummer'], hashed_password)
    cursor.execute(query, values)
    connection.commit()
    
    # Send email notification
    admin_email = "admin@example.com"  # Replace with actual admin email
    subject = "Nieuwe aanmelding"
    body = f"Er is een nieuwe aanmelding van chef {data['name']} met email {data['email']} en telefoonnummer {data['telefoonnummer']}."
    send_email(admin_email, subject, body)
    
    # Send verification email to chef
    verification_link = f"http://example.com/verify?email={data['email']}"  # Replace with actual verification link
    subject = "Verificatie van uw account"
    body = f"Beste {data['name']},\n\nKlik op de volgende link om uw account te verifiëren: {verification_link}"
    send_email(data['email'], subject, body)
    
    return jsonify({"message": "Chef account created successfully"}), 201

@app.route("/register", methods=["GET"])
def register_form():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    naam = request.form['naam']
    email = request.form['email']
    telefoonnummer = request.form['telefoonnummer']
    password = request.form['password']
    linkedin = request.form.get('linkedin', '')

    hashed_password = generate_password_hash(password)
    
    cursor = connection.cursor()
    query = "INSERT INTO chefs (naam, email, telefoonnummer, password, linkedin) VALUES (%s, %s, %s, %s, %s)"
    values = (naam, email, telefoonnummer, hashed_password, linkedin)
    cursor.execute(query, values)
    connection.commit()
    
    return redirect(url_for('home'))

@app.route('/')
def index():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM ingredient")
    ingredients = cursor.fetchall()
    return render_template('index.html', ingredients=ingredients)

@app.route('/add_gerecht', methods=['POST'])
def add_gerecht():
    naam = request.form['naam']
    beschrijving = request.form['beschrijving']
    prijs = request.form['prijs']
    menu = request.form['menu']
    chef_id = request.form['chef_id']
    
    cursor = connection.cursor()
    cursor.execute("INSERT INTO gerecht (naam, beschrijving, prijs, menu, chef_id) VALUES (%s, %s, %s, %s, %s)", (naam, beschrijving, prijs, menu, chef_id))
    connection.commit()
    
    gerecht_id = cursor.lastrowid
    ingredienten = request.form.getlist('ingredient')
    hoeveelheden = request.form.getlist('hoeveelheid')
    
    for ingredient_id, hoeveelheid in zip(ingredienten, hoeveelheden):
        cursor.execute("INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid, chef_id) VALUES (%s, %s, %s, %s)", (gerecht_id, ingredient_id, hoeveelheid, chef_id))
    
    connection.commit()
    return redirect(url_for('gerechten', chef_id=chef_id))

@app.route("/add_ingredient", methods=["GET"])
def add_ingredient_form():
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM units")
    units = cursor.fetchall()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    return render_template("add_ingredient.html", units=units, categories=categories)

@app.route("/add_ingredient", methods=["POST"])
def add_ingredient():
    naam = request.form['naam']
    eenheid = request.form['eenheid']
    prijs = request.form['prijs']
    categorie = request.form['categorie']
    
    cursor = connection.cursor()
    cursor.execute("INSERT INTO ingredient (naam, eenheid, prijs, categorie) VALUES (%s, %s, %s, %s)", (naam, eenheid, prijs, categorie))
    connection.commit()
    
    return redirect(url_for('inventory'))

@app.route("/manage_ingredients", methods=["GET"])
def manage_ingredients():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM ingredient")
    ingredients = cursor.fetchall()
    return render_template("manage_ingredients.html", ingredients=ingredients)

@app.route("/gerecht_aanmaken", methods=["GET", "POST"])
def gerecht_aanmaken():
    if 'chef_id' not in session:
        return redirect(url_for('login'))

    cursor = connection.cursor(dictionary=True)
    
    if request.method == "POST":
        naam = request.form['naam']
        beschrijving = request.form['beschrijving']
        prijs = request.form['prijs']
        menu = request.form['menu']
        chef_id = session['chef_id']
        
        cursor.execute(
            "INSERT INTO gerecht (naam, beschrijving, prijs, menu, chef_id) VALUES (%s, %s, %s, %s, %s)",
            (naam, beschrijving, prijs, menu, chef_id)
        )
        connection.commit()
        
        gerecht_id = cursor.lastrowid
        ingredienten = request.form.getlist('ingredient')
        hoeveelheden = request.form.getlist('hoeveelheid')
        
        for ingredient_id, hoeveelheid in zip(ingredienten, hoeveelheden):
            cursor.execute(
                "INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid, chef_id) "
                "VALUES (%s, %s, %s, %s)",
                (gerecht_id, ingredient_id, hoeveelheid, chef_id)
            )
        connection.commit()
        return redirect(url_for('gerechten', chef_id=chef_id))

    cursor.execute("SELECT * FROM ingredient")
    ingredients = cursor.fetchall()

    return render_template("gerecht_aanmaken.html", ingredients=ingredients)

@app.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chefs WHERE email = %s", (email,))
        chef = cursor.fetchone()
        
        if chef and check_password_hash(chef['password'], password):
            session['chef_id'] = chef['id']
            session['chef_naam'] = chef['naam']
            return redirect(url_for('personal_dashboard', chef_id=chef['id']))
        else:
            return "Ongeldige inloggegevens", 401
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/dashboard/<int:chef_id>")
def personal_dashboard(chef_id):
    if 'chef_id' not in session or session['chef_id'] != chef_id:
        return redirect(url_for('login'))
    
    naam = session.get('chef_naam')
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM gerecht WHERE chef_id = %s", (chef_id,))
    gerechten = cursor.fetchall()
    
    return render_template("personal_dashboard.html", naam=naam, gerechten=gerechten)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form['email']
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chefs WHERE email = %s", (email,))
        chef = cursor.fetchone()
        
        if chef:
            # Generate a password reset link (this is a placeholder, implement actual logic)
            reset_link = f"http://example.com/reset_password?email={email}"
            subject = "Wachtwoord Herstellen"
            body = f"Beste {chef['naam']},\n\nKlik op de volgende link om uw wachtwoord te herstellen: {reset_link}"
            send_email(email, subject, body)
            return "Een e-mail met instructies om uw wachtwoord te herstellen is verzonden."
        else:
            return "Geen account gevonden met dit e-mailadres.", 404
    
    return render_template("forgot_password.html")

@app.route("/inventory", methods=["GET"])
def inventory():
    categorie = request.args.get('categorie', '')
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    if categorie:
        cursor.execute("SELECT id, naam, eenheid, prijs, categorie FROM ingredient WHERE categorie = %s", (categorie,))
    else:
        cursor.execute("SELECT id, naam, eenheid, prijs, categorie FROM ingredient")
    
    ingredients = cursor.fetchall()
    return render_template("inventory.html", ingredients=ingredients, categories=categories)

@app.route("/edit_ingredient", methods=["POST"])
def edit_ingredient():
    id = request.form['id']
    naam = request.form['naam']
    eenheid = request.form['eenheid']
    prijs = request.form['prijs']
    categorie = request.form['categorie']
    
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE ingredient
        SET naam = %s, eenheid = %s, prijs = %s, categorie = %s
        WHERE id = %s
    """, (naam, eenheid, prijs, categorie, id))
    connection.commit()
    
    return redirect(url_for('inventory'))

@app.route("/delete_ingredient", methods=["POST"])
def delete_ingredient():
    id = request.form['id']
    
    cursor = connection.cursor()
    cursor.execute("DELETE FROM ingredient WHERE id = %s", (id,))
    connection.commit()
    
    return redirect(url_for('inventory'))

@app.route("/gerechten/<int:chef_id>", methods=["GET"])
def gerechten(chef_id):
    if 'chef_id' not in session or session['chef_id'] != chef_id:
        return redirect(url_for('login'))
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM gerecht WHERE chef_id = %s", (chef_id,))
    gerechten = cursor.fetchall()
    
    return render_template("gerechten.html", gerechten=gerechten)

@app.route("/edit_gerecht/<int:id>", methods=["GET", "POST"])
def edit_gerecht(id):
    cursor = connection.cursor(dictionary=True)
    
    if request.method == "POST":
        naam = request.form['naam']
        beschrijving = request.form['beschrijving']
        prijs = request.form['prijs']
        menu = request.form['menu']
        
        cursor.execute("""
            UPDATE gerecht
            SET naam = %s, beschrijving = %s, prijs = %s, menu = %s
            WHERE id = %s
        """, (naam, beschrijving, prijs, menu, id))
        connection.commit()
        
        # Update ingredients
        ingredienten = request.form.getlist('ingredient')
        hoeveelheden = request.form.getlist('hoeveelheid')
        
        existing_ingredients = {ingredient['ingredient_id']: ingredient['hoeveelheid'] for ingredient in cursor.execute("SELECT ingredient_id, hoeveelheid FROM gerecht_ingredient WHERE gerecht_id = %s", (id,)).fetchall()}
        
        for ingredient_id, hoeveelheid in zip(ingredienten, hoeveelheden):
            if ingredient_id in existing_ingredients:
                cursor.execute("""
                    UPDATE gerecht_ingredient
                    SET hoeveelheid = %s
                    WHERE gerecht_id = %s AND ingredient_id = %s
                """, (hoeveelheid, id, ingredient_id))
            else:
                cursor.execute("""
                    INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid, chef_id)
                    VALUES (%s, %s, %s, %s)
                """, (id, ingredient_id, hoeveelheid, session['chef_id']))
        
        connection.commit()
        
        return redirect(url_for('gerechten', chef_id=session['chef_id']))
    
    cursor.execute("SELECT * FROM gerecht WHERE id = %s", (id,))
    gerecht = cursor.fetchone()
    
    cursor.execute("SELECT gi.ingredient_id, gi.hoeveelheid, i.naam, i.prijs FROM gerecht_ingredient gi JOIN ingredient i ON gi.ingredient_id = i.id WHERE gi.gerecht_id = %s", (id,))
    gerecht_ingredienten = cursor.fetchall()
    
    cursor.execute("SELECT * FROM ingredient")
    ingredients = cursor.fetchall()
    
    return render_template("edit_gerecht.html", gerecht=gerecht, gerecht_ingredienten=gerecht_ingredienten, ingredients=ingredients)

@app.route("/view_gerecht/<int:id>", methods=["GET"])
def view_gerecht(id):
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM gerecht WHERE id = %s", (id,))
    gerecht = cursor.fetchone()
    
    cursor.execute("SELECT gi.ingredient_id, gi.hoeveelheid, i.naam, i.prijs FROM gerecht_ingredient gi JOIN ingredient i ON gi.ingredient_id = i.id WHERE gi.gerecht_id = %s", (id,))
    gerecht_ingredienten = cursor.fetchall()
    
    return render_template("view_gerecht.html", gerecht=gerecht, gerecht_ingredienten=gerecht_ingredienten)

@app.route("/manage_gerecht_ingredients/<int:chef_id>", methods=["GET", "POST"])
def manage_gerecht_ingredients(chef_id):
    if 'chef_id' not in session or session['chef_id'] != chef_id:
        return redirect(url_for('login'))

    cursor = connection.cursor(dictionary=True)
    
    if request.method == "POST":
        action = request.form.get('action')
        gerecht_id = request.form.get('gerecht_id')
        ingredient_id = request.form.get('ingredient_id')
        hoeveelheid = request.form.get('hoeveelheid')

        if action == "add":
            cursor.execute(
                "INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid, chef_id) "
                "VALUES (%s, %s, %s, %s)",
                (gerecht_id, ingredient_id, hoeveelheid, chef_id)
            )
        elif action == "remove":
            cursor.execute(
                "DELETE FROM gerecht_ingredient WHERE gerecht_id = %s AND ingredient_id = %s",
                (gerecht_id, ingredient_id)
            )
        connection.commit()

    cursor.execute("SELECT * FROM gerecht WHERE chef_id = %s", (chef_id,))
    gerechten = cursor.fetchall()

    # Haal voor elk gerecht de gekoppelde ingrediënten op
    gerecht_ingredients = {}
    for g in gerechten:
        cursor.execute(
            "SELECT gi.ingredient_id, gi.hoeveelheid, i.naam "
            "FROM gerecht_ingredient gi JOIN ingredient i ON gi.ingredient_id = i.id "
            "WHERE gi.gerecht_id = %s", (g['id'],)
        )
        gerecht_ingredients[g['id']] = cursor.fetchall()

    cursor.execute("SELECT * FROM ingredient")
    all_ingredients = cursor.fetchall()

    return render_template(
        "manage_gerecht_ingredients.html",
        gerechten=gerechten,
        gerecht_ingredients=gerecht_ingredients,
        all_ingredients=all_ingredients
    )

@app.route("/delete_gerecht/<int:id>", methods=["POST"])
def delete_gerecht(id):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM gerecht WHERE id = %s", (id,))
    cursor.execute("DELETE FROM gerecht_ingredient WHERE gerecht_id = %s", (id,))
    connection.commit()
    return redirect(url_for('gerechten', chef_id=session['chef_id']))

@app.route("/test_gerecht_ingredient", methods=["GET", "POST"])
def test_gerecht_ingredient():
    if 'chef_id' not in session:
        return redirect(url_for('login'))

    cursor = connection.cursor(dictionary=True)
    
    if request.method == "POST":
        gerecht_id = request.form.get('gerecht_id')
        ingredient_id = request.form.get('ingredient_id')
        hoeveelheid = request.form.get('hoeveelheid')
        
        cursor.execute(
            "INSERT INTO gerecht_ingredient (gerecht_id, ingredient_id, hoeveelheid, chef_id) "
            "VALUES (%s, %s, %s, %s)",
            (gerecht_id, ingredient_id, hoeveelheid, session['chef_id'])
        )
        connection.commit()

    cursor.execute("SELECT * FROM gerecht WHERE chef_id = %s", (session['chef_id'],))
    gerechten = cursor.fetchall()

    cursor.execute("SELECT * FROM ingredient")
    ingredients = cursor.fetchall()

    cursor.execute("""
        SELECT gi.gerecht_id, g.naam AS gerecht_naam, gi.ingredient_id, i.naam AS ingredient_naam, gi.hoeveelheid
        FROM gerecht_ingredient gi
        JOIN gerecht g ON gi.gerecht_id = g.id
        JOIN ingredient i ON gi.ingredient_id = i.id
        WHERE g.chef_id = %s
    """, (session['chef_id'],))
    gerecht_ingredienten = cursor.fetchall()

    return render_template(
        "test_gerecht_ingredient.html",
        gerechten=gerechten,
        ingredients=ingredients,
        gerecht_ingredienten=gerecht_ingredienten
    )

if __name__ == '__main__':
    app.run(debug=True)
