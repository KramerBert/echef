from flask import render_template, redirect, url_for, flash, request, session, jsonify
from werkzeug.security import check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from utils.db import get_db_connection
from . import bp
import logging

logger = logging.getLogger(__name__)

class AdminLoginForm(FlaskForm):
    email = StringField('E-mailadres', validators=[DataRequired(), Email()])
    password = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Inloggen')

# Admin login vereist decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Toegang geweigerd. Log in als beheerder.", "danger")
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login route"""
    # Check if already logged in
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))
        
    form = AdminLoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        conn = get_db_connection()
        if not conn:
            flash("Database verbinding mislukt", "danger")
            return render_template('admin/login.html', form=form)
            
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM admins WHERE email = %s", (email,))
            admin = cur.fetchone()
            
            if admin and check_password_hash(admin['password_hash'], password):
                session['admin_id'] = admin['admin_id']
                session['admin_username'] = admin['username']
                session['admin_email'] = admin['email']
                flash("Succesvol ingelogd als beheerder!", "success")
                return redirect(url_for('admin.dashboard'))
            else:
                flash("Ongeldige inloggegevens", "danger")
        except Exception as e:
            logger.error(f"Admin login error: {str(e)}")
            flash("Er is een fout opgetreden bij het inloggen", "danger")
        finally:
            cur.close()
            conn.close()
            
    return render_template('admin/login.html', form=form)

@bp.route('/logout')
def logout():
    """Admin logout route"""
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash("U bent uitgelogd als beheerder", "success")
    return redirect(url_for('admin.login'))

@bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard route"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.login'))
        
    cur = conn.cursor(dictionary=True)
    try:
        # Haal statistieken op voor het dashboard
        cur.execute("SELECT COUNT(*) as total_chefs FROM chefs")
        chefs_count = cur.fetchone()['total_chefs']
        
        cur.execute("SELECT COUNT(*) as total_dishes FROM dishes")
        dishes_count = cur.fetchone()['total_dishes']
        
        cur.execute("SELECT COUNT(*) as total_ingredients FROM ingredients")
        ingredients_count = cur.fetchone()['total_ingredients']
        
        # Simplified query that doesn't reference non-existent columns
        cur.execute("""
            SELECT c.chef_id, c.naam, c.email,
                   (SELECT COUNT(*) FROM dishes WHERE chef_id = c.chef_id) as dish_count,
                   (SELECT COUNT(*) FROM ingredients WHERE chef_id = c.chef_id) as ingredient_count
            FROM chefs c
            ORDER BY c.chef_id DESC
        """)
        chefs = cur.fetchall()
        
        return render_template('admin/dashboard.html', 
                              chefs_count=chefs_count,
                              dishes_count=dishes_count,
                              ingredients_count=ingredients_count,
                              chefs=chefs)
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        flash("Er is een fout opgetreden bij het laden van het dashboard", "danger")
        return redirect(url_for('admin.login'))
    finally:
        cur.close()
        conn.close()

@bp.route('/chef/<int:chef_id>/details')
@admin_required
def chef_details(chef_id):
    """Toon gedetailleerde informatie over een chef"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.dashboard'))
        
    cur = conn.cursor(dictionary=True)
    try:
        # Haal chef informatie op
        cur.execute("SELECT * FROM chefs WHERE chef_id = %s", (chef_id,))
        chef = cur.fetchone()
        
        if not chef:
            flash("Chef niet gevonden", "danger")
            return redirect(url_for('admin.dashboard'))
        
        # Haal dishes op voor deze chef
        cur.execute("SELECT * FROM dishes WHERE chef_id = %s", (chef_id,))
        dishes = cur.fetchall()
        
        # Haal ingrediënten op voor deze chef
        cur.execute("SELECT * FROM ingredients WHERE chef_id = %s LIMIT 100", (chef_id,))
        ingredients = cur.fetchall()
        
        # Andere informatie zoals HACCP records, etc.
        cur.execute("SELECT * FROM haccp_checklists WHERE chef_id = %s", (chef_id,))
        haccp_checklists = cur.fetchall()
        
        return render_template('admin/chef_details.html', 
                              chef=chef,
                              dishes=dishes,
                              ingredients=ingredients,
                              haccp_checklists=haccp_checklists)
    except Exception as e:
        logger.error(f"Chef details error: {str(e)}")
        flash(f"Er is een fout opgetreden: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))
    finally:
        cur.close()
        conn.close()

@bp.route('/chef/<int:chef_id>/delete', methods=['POST'])
@admin_required
def delete_chef(chef_id):
    """Verwijder een chef en alle bijbehorende gegevens"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.dashboard'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Begin een transactie
        conn.start_transaction()
        
        # Haal eerst de chef informatie op om te bevestigen dat deze bestaat
        cur.execute("SELECT * FROM chefs WHERE chef_id = %s", (chef_id,))
        chef = cur.fetchone()
        
        if not chef:
            conn.rollback()
            flash("Chef niet gevonden", "danger")
            return redirect(url_for('admin.dashboard'))
        
        # Verwijder alle gerelateerde records in de juiste volgorde
        # Eerst dish_allergenen en dish_dieten omdat deze foreign keys hebben naar dishes
        cur.execute("""
            DELETE da FROM dish_allergenen da
            JOIN dishes d ON da.dish_id = d.dish_id
            WHERE d.chef_id = %s
        """, (chef_id,))
        
        cur.execute("""
            DELETE dd FROM dish_dieten dd
            JOIN dishes d ON dd.dish_id = d.dish_id
            WHERE d.chef_id = %s
        """, (chef_id,))
        
        # Verwijder dish_ingredients
        cur.execute("""
            DELETE di FROM dish_ingredients di
            JOIN dishes d ON di.dish_id = d.dish_id
            WHERE d.chef_id = %s
        """, (chef_id,))
        
        # NIEUW: Verwijder haccp_temperatuur records
        cur.execute("DELETE FROM haccp_temperatuur WHERE chef_id = %s", (chef_id,))
        
        # NIEUW: Verwijder haccp_schoonmaak_planning records
        cur.execute("DELETE FROM haccp_schoonmaak_planning WHERE chef_id = %s", (chef_id,))
        
        # NIEUW: Verwijder haccp_productie records
        cur.execute("DELETE FROM haccp_productie WHERE chef_id = %s", (chef_id,))
        
        # NIEUW: Verwijder haccp_ongedierte records
        cur.execute("DELETE FROM haccp_ongedierte WHERE chef_id = %s", (chef_id,))
        
        # NIEUW: Verwijder haccp_allergenen_controle records
        cur.execute("DELETE FROM haccp_allergenen_controle WHERE chef_id = %s", (chef_id,))
        
        # NIEUW: Verwijder haccp_hygiene_controle records
        cur.execute("DELETE FROM haccp_hygiene_controle WHERE chef_id = %s", (chef_id,))
        
        # Verwijder haccp metingen
        cur.execute("""
            DELETE m FROM haccp_metingen m
            JOIN haccp_checkpunten p ON m.punt_id = p.punt_id
            JOIN haccp_checklists c ON p.checklist_id = c.checklist_id
            WHERE c.chef_id = %s
        """, (chef_id,))
        
        # Verwijder haccp_checkpunten
        cur.execute("""
            DELETE p FROM haccp_checkpunten p
            JOIN haccp_checklists c ON p.checklist_id = c.checklist_id
            WHERE c.chef_id = %s
        """, (chef_id,))
        
        # Verwijder haccp_checklists
        cur.execute("DELETE FROM haccp_checklists WHERE chef_id = %s", (chef_id,))
        
        # Verwijder dishes
        cur.execute("DELETE FROM dishes WHERE chef_id = %s", (chef_id,))
        
        # Verwijder ingredients
        cur.execute("DELETE FROM ingredients WHERE chef_id = %s", (chef_id,))
        
        # Verwijder leveranciers
        cur.execute("DELETE FROM leveranciers WHERE chef_id = %s", (chef_id,))
        
        # Verwijder categorieen
        cur.execute("DELETE FROM categorieen WHERE chef_id = %s", (chef_id,))
        
        # Verwijder eenheden
        cur.execute("DELETE FROM eenheden WHERE chef_id = %s", (chef_id,))
        
        # Verwijder dish_categories
        cur.execute("DELETE FROM dish_categories WHERE chef_id = %s", (chef_id,))
        
        # Verwijder de chef zelf
        cur.execute("DELETE FROM chefs WHERE chef_id = %s", (chef_id,))
        
        # Commit de transactie als alles succesvol is
        conn.commit()
        
        flash(f"Chef {chef['naam']} ({chef['email']}) en alle gerelateerde gegevens zijn succesvol verwijderd!", "success")
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        # Rollback bij fout
        conn.rollback()
        logger.error(f"Delete chef error: {str(e)}")
        flash(f"Er is een fout opgetreden bij het verwijderen van de chef: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))
    finally:
        cur.close()
        conn.close()

@bp.route('/chef/<int:chef_id>/toggle_status', methods=['POST'])
@admin_required
def toggle_chef_status(chef_id):
    """Activeer of deactiveer een chef account"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database verbinding mislukt"}), 500
    
    cur = conn.cursor(dictionary=True)
    try:
        # Haal huidige status op
        cur.execute("SELECT active FROM chefs WHERE chef_id = %s", (chef_id,))
        chef = cur.fetchone()
        
        if not chef:
            return jsonify({"success": False, "error": "Chef niet gevonden"}), 404
        
        # Toggle status
        new_status = 0 if chef['active'] == 1 else 1
        cur.execute("UPDATE chefs SET active = %s WHERE chef_id = %s", (new_status, chef_id))
        conn.commit()
        
        status_text = "geactiveerd" if new_status == 1 else "gedeactiveerd"
        return jsonify({
            "success": True, 
            "message": f"Chef {status_text}",
            "new_status": new_status
        })
    except Exception as e:
        logger.error(f"Toggle chef status error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
