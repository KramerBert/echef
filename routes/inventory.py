from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from functools import wraps
from flask import session
from datetime import datetime
from utils.db import get_db_connection
import logging

bp = Blueprint('inventory', __name__, url_prefix='/inventory')
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'chef_id' not in session:
            flash("Geen toegang. Log opnieuw in.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/', methods=['GET'])
def index():
    """Show inventory items for the current chef"""
    db = get_db_connection()
    chef_naam = session.get('chef_naam')
    
    if not chef_naam:
        return redirect(url_for('auth.login'))
    
    items = db.execute(
        'SELECT * FROM inventory WHERE chef_naam = ?',
        (chef_naam,)
    ).fetchall()
    
    return render_template('inventory/index.html', items=items)

@bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new inventory item"""
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        unit = request.form['unit']
        chef_naam = session.get('chef_naam')
        error = None
        
        if not name:
            error = 'Naam is verplicht.'
        
        if error is None:
            db = get_db_connection()
            db.execute(
                'INSERT INTO inventory (chef_naam, name, quantity, unit) VALUES (?, ?, ?, ?)',
                (chef_naam, name, quantity, unit)
            )
            db.commit()
            return redirect(url_for('inventory.index'))
            
        flash(error)
        
    return render_template('inventory/add.html')

@bp.route('/dashboard/<chef_naam>/inventory/reports')
@login_required
def list_reports(chef_naam):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))

    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT * FROM inventory_reports 
            WHERE chef_id = %s 
            ORDER BY report_date DESC
        """, (session['chef_id'],))
        reports = cur.fetchall()
        
        return render_template('inventory/list_reports.html', 
                             chef_naam=chef_naam, 
                             reports=reports)
    finally:
        cur.close()
        conn.close()

@bp.route('/dashboard/<chef_naam>/inventory/new', methods=['GET', 'POST'])
@login_required
def create_report(chef_naam):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name')
        report_date = request.form.get('report_date')

        if not name or not report_date:
            flash("Naam en datum zijn verplicht.", "danger")
            return redirect(url_for('inventory.create_report', chef_naam=chef_naam))

        conn = get_db_connection()
        if not conn:
            flash("Database verbinding mislukt.", "danger")
            return redirect(url_for('inventory.list_reports', chef_naam=chef_naam))

        cur = conn.cursor()
        try:
            # Maak het rapport aan
            cur.execute("""
                INSERT INTO inventory_reports (chef_id, name, report_date)
                VALUES (%s, %s, %s)
            """, (session['chef_id'], name, report_date))
            
            report_id = cur.lastrowid
            
            # Kopieer alle ingrediënten naar report_items met quantity 0
            cur.execute("""
                INSERT INTO inventory_report_items (report_id, ingredient_id, quantity)
                SELECT %s, ingredient_id, 0
                FROM ingredients
                WHERE chef_id = %s
            """, (report_id, session['chef_id']))
            
            conn.commit()
            flash("Voorraadrapport aangemaakt!", "success")
            return redirect(url_for('inventory.edit_report', 
                                  chef_naam=chef_naam, 
                                  report_id=report_id))
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij aanmaken rapport: {str(e)}", "danger")
            return redirect(url_for('inventory.list_reports', chef_naam=chef_naam))
        finally:
            cur.close()
            conn.close()

    return render_template('inventory/create_report.html', chef_naam=chef_naam)

@bp.route('/dashboard/<chef_naam>/inventory/report/<int:report_id>')
@login_required
def edit_report(chef_naam, report_id):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt.", "danger")
        return redirect(url_for('inventory.list_reports', chef_naam=chef_naam))

    cur = conn.cursor(dictionary=True)
    try:
        # Haal rapport info op
        cur.execute("""
            SELECT * FROM inventory_reports 
            WHERE report_id = %s AND chef_id = %s
        """, (report_id, session['chef_id']))
        report = cur.fetchone()

        if not report:
            flash("Rapport niet gevonden.", "danger")
            return redirect(url_for('inventory.list_reports', chef_naam=chef_naam))

        # Haal alle ingrediënten met hun huidige voorraad op
        cur.execute("""
            SELECT i.*, ri.quantity as current_quantity, 
                   (i.prijs_per_eenheid * ri.quantity) as subtotal
            FROM ingredients i
            LEFT JOIN inventory_report_items ri ON i.ingredient_id = ri.ingredient_id 
            WHERE i.chef_id = %s AND (ri.report_id = %s OR ri.report_id IS NULL)
            ORDER BY i.naam
        """, (session['chef_id'], report_id))
        ingredients = cur.fetchall()

        # Bereken totale waarde
        total_value = sum(float(ing['subtotal'] or 0) for ing in ingredients)

        return render_template('inventory/edit_report.html',
                             chef_naam=chef_naam,
                             report=report,
                             ingredients=ingredients,
                             total_value=total_value)
    finally:
        cur.close()
        conn.close()

@bp.route('/dashboard/<chef_naam>/inventory/report/<int:report_id>/update', methods=['POST'])
@login_required
def update_report_item(chef_naam, report_id):
    if session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    data = request.get_json()
    ingredient_id = data.get('ingredient_id')
    quantity = data.get('quantity', 0)

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

    cur = conn.cursor()
    try:
        # Update de voorraad
        cur.execute("""
            INSERT INTO inventory_report_items (report_id, ingredient_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = VALUES(quantity)
        """, (report_id, ingredient_id, quantity))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()
