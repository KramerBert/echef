from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash
from utils.db import get_db_connection
from blueprints.auth.utils import hash_password

bp = Blueprint('profile', __name__, url_prefix='/dashboard', template_folder='templates')

@bp.route('/<chef_naam>/profile', methods=['GET', 'POST'])
def profile(chef_naam):
    form = FlaskForm()
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Onvoldoende rechten om dit profiel te bekijken.", "danger")
        return redirect(url_for('home'))

    conn = get_db_connection()
    if conn is None:
        flash("Database verbindingsfout.", "danger") 
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("SELECT * FROM chefs WHERE chef_id = %s", (session['chef_id'],))
        chef = cur.fetchone()

        if request.method == 'POST' and form.validate_on_submit():
            if 'update_password' in request.form:
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                if not check_password_hash(chef['wachtwoord'], current_password):
                    flash("Huidig wachtwoord is onjuist.", "danger")
                    return redirect(url_for('profile.profile', chef_naam=chef_naam))

                if new_password != confirm_password:
                    flash("Nieuwe wachtwoorden komen niet overeen.", "danger")
                    return redirect(url_for('profile.profile', chef_naam=chef_naam))

                hashed_password = hash_password(new_password)
                cur.execute("""
                    UPDATE chefs 
                    SET wachtwoord = %s 
                    WHERE chef_id = %s
                """, (hashed_password, session['chef_id']))
                conn.commit()
                flash("Wachtwoord succesvol bijgewerkt.", "success")
                return redirect(url_for('profile.profile', chef_naam=chef_naam))

        return render_template('profile/profile.html', 
                            chef_naam=chef_naam,
                            chef=chef,
                            form=form)

    except Exception as e:
        flash("Er is een fout opgetreden bij het laden van het profiel.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/delete_account', methods=['POST'])
def delete_account(chef_naam):
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('profile.profile', chef_naam=chef_naam))

    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    cur = conn.cursor()

    try:
        chef_id = session['chef_id']
        cur.execute("START TRANSACTION")
            
        # Delete all related data in correct order
        cur.execute("DELETE FROM dish_allergenen WHERE dish_id IN (SELECT dish_id FROM dishes WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM dish_dieten WHERE dish_id IN (SELECT dish_id FROM dishes WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM dish_ingredients WHERE dish_id IN (SELECT dish_id FROM dishes WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM dishes WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM ingredients WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM leveranciers WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM haccp_metingen WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM haccp_checkpunten WHERE checklist_id IN (SELECT checklist_id FROM haccp_checklists WHERE chef_id = %s)", (chef_id,))
        cur.execute("DELETE FROM haccp_checklists WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM eenheden WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM categorieen WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM dish_categories WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM password_resets WHERE chef_id = %s", (chef_id,))
        cur.execute("DELETE FROM chefs WHERE chef_id = %s", (chef_id,))
            
        conn.commit()
        session.clear()
        flash("Je account is succesvol verwijderd.", "success")
        return redirect(url_for('home'))
            
    except Exception as e:
        conn.rollback()
        flash("Er is een fout opgetreden bij het verwijderen van je account.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()
