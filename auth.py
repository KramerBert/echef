from flask import (
    Blueprint, flash, redirect, render_template, 
    request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import get_db_connection

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()
        error = None

        # Vervang spaties door underscores voor de database
        username_db = username.replace(' ', '_')  # voor database opslag
        username_display = username  # originele versie met spaties voor weergave

        if not username:
            error = 'Gebruikersnaam is verplicht.'
        elif not password:
            error = 'Wachtwoord is verplicht.'

        if error is None:
            try:
                # Sla de gebruiker op met de underscore versie
                db.execute(
                    'INSERT INTO user (username, password) VALUES (?, ?)',
                    (username_db, generate_password_hash(password))
                )
                db.commit()
                
                # Sla beide versies op in de sessie
                session['chef_naam'] = username_db  # voor URL/database gebruik
                session['chef_display_naam'] = username_display  # voor weergave
                
                return redirect(url_for('dashboard', chef_naam=username_db))
            except db.IntegrityError:
                error = f"Gebruiker {username} bestaat al."

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()  # Updated function name
        
        # Converteer input naar database formaat
        username_db = username.replace(' ', '_')
        
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username_db,)
        ).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            error = 'Incorrecte gebruikersnaam of wachtwoord.'
            flash(error)
            return render_template('auth/login.html')

        session.clear()
        session['chef_id'] = user['id']
        session['chef_naam'] = username_db  # voor URL/database gebruik
        session['chef_display_naam'] = username.replace('_', ' ')  # voor weergave
        
        return redirect(url_for('dashboard', chef_naam=username_db))

    return render_template('auth/login.html')
