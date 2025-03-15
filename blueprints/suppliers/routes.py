from flask import (
    render_template, redirect, url_for, flash, request, 
    session, current_app, jsonify
)
from markupsafe import Markup
from . import bp
from utils.db import get_db_connection
import logging

# Set up logging
logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to ensure user is logged in"""
    def decorated_function(*args, **kwargs):
        if 'chef_id' not in session:
            flash("Je moet ingelogd zijn om deze pagina te bekijken.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_or_create_supplier(chef_id, naam, contact=None, telefoon=None, email=None, is_admin_created=False):
    """
    Get existing supplier or create a new one if it doesn't exist
    
    Args:
        chef_id (int): Chef ID
        naam (str): Supplier name
        contact (str, optional): Contact person
        telefoon (str, optional): Phone number
        email (str, optional): Email address
        is_admin_created (bool): Whether this supplier is admin created
        
    Returns:
        tuple: (supplier_id, created) where created is True if a new supplier was created
    """
    conn = get_db_connection()
    if conn is None:
        return None, False
        
    cur = conn.cursor(dictionary=True)
    created = False
    supplier_id = None
    
    try:
        # Check if supplier exists
        cur.execute("""
            SELECT leverancier_id FROM leveranciers
            WHERE chef_id = %s AND naam = %s
        """, (chef_id, naam))
        
        existing = cur.fetchone()
        
        if existing:
            supplier_id = existing['leverancier_id']
            
            # Update supplier info if provided
            if contact is not None or telefoon is not None or email is not None:
                update_fields = []
                params = []
                
                if contact is not None:
                    update_fields.append("contact = %s")
                    params.append(contact)
                
                if telefoon is not None:
                    update_fields.append("telefoon = %s")
                    params.append(telefoon)
                
                if email is not None:
                    update_fields.append("email = %s")
                    params.append(email)
                
                if update_fields:
                    query = f"UPDATE leveranciers SET {', '.join(update_fields)} WHERE leverancier_id = %s"
                    params.append(supplier_id)
                    
                    cur.execute(query, tuple(params))
                    conn.commit()
        else:
            # Create new supplier
            cur.execute("""
                INSERT INTO leveranciers (chef_id, naam, contact, telefoon, email, is_admin_created)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (chef_id, naam, contact, telefoon, email, is_admin_created))
            
            supplier_id = cur.lastrowid
            created = True
            conn.commit()
            
        return supplier_id, created
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_supplier: {str(e)}")
        return None, False
    finally:
        cur.close()
        conn.close()

@bp.route('/api/get_or_create_supplier', methods=['POST'])
@login_required
def api_get_or_create_supplier():
    """API endpoint to get or create a supplier"""
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
    supplier_id, created = get_or_create_supplier(
        session['chef_id'],
        data['name'],
        data.get('contact'),
        data.get('phone'),
        data.get('email'),
        data.get('is_admin_created', False)
    )
    
    if supplier_id:
        return jsonify({
            'success': True,
            'supplier_id': supplier_id,
            'created': created
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to process supplier'}), 500

@bp.route('/dashboard/<chef_naam>/suppliers', methods=['GET', 'POST'])
@login_required
def manage_suppliers(chef_naam):
    """Manage suppliers for a chef"""
    if session.get('chef_naam') != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get user's suppliers
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE chef_id = %s AND is_admin_created = FALSE
            ORDER BY naam
        """, (session['chef_id'],))
        leveranciers = cur.fetchall()
        
        # Get system suppliers created by admins
        cur.execute("""
            SELECT l.*, 
                   (SELECT COUNT(*) FROM system_ingredients si WHERE si.leverancier_id = l.leverancier_id) AS ingredient_count
            FROM leveranciers l
            WHERE l.is_admin_created = TRUE
            ORDER BY l.naam
        """)
        system_leveranciers = cur.fetchall()
        
        return render_template('manage_suppliers.html',
                              chef_naam=chef_naam,
                              leveranciers=leveranciers,
                              system_leveranciers=system_leveranciers)
    except Exception as e:
        logger.error(f"Error fetching suppliers: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

@bp.route('/dashboard/<chef_naam>/suppliers/<leverancier_id>/delete', methods=['POST'])
@login_required
def delete_supplier(chef_naam, leverancier_id):
    if session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Unauthorized'})

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'})

    cur = conn.cursor(dictionary=True)
    try:
        # First check if this is an admin-created supplier
        cur.execute("""
            SELECT is_admin_created FROM leveranciers 
            WHERE leverancier_id = %s
        """, (leverancier_id,))
        
        supplier = cur.fetchone()
        if not supplier:
            return jsonify({'success': False, 'error': 'Supplier not found'})
        
        # Prevent deletion if it's an admin supplier
        if supplier.get('is_admin_created'):
            return jsonify({'success': False, 'error': 'Cannot delete system suppliers'})
        
        # Continue with existing deletion code for chef's personal suppliers
        # Controleer of de leverancier bestaat en bij deze chef hoort
        cur.execute("""
            SELECT leverancier_id 
            FROM leveranciers 
            WHERE leverancier_id = %s AND chef_id = %s
        """, (leverancier_id, session['chef_id']))
        
        if not cur.fetchone():
            return jsonify({'success': False, 'error': 'Supplier not found or unauthorized'})

        # Update eerst alle ingrediënten die deze leverancier gebruiken
        cur.execute("""
            UPDATE ingredients 
            SET leverancier_id = NULL 
            WHERE leverancier_id = %s AND chef_id = %s
        """, (leverancier_id, session['chef_id']))

        # Verwijder dan de leverancier
        cur.execute("""
            DELETE FROM leveranciers 
            WHERE leverancier_id = %s AND chef_id = %s
        """, (leverancier_id, session['chef_id']))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        logger.error(f'Error deleting supplier: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()
        conn.close()

@bp.route('/dashboard/<chef_naam>/suppliers/<int:leverancier_id>/edit', methods=['POST'])
@login_required
def edit_supplier(chef_naam, leverancier_id):
    if session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Unauthorized'})

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'})

    cur = conn.cursor()
    try:
        naam = request.form.get('naam')
        contact = request.form.get('contact')
        telefoon = request.form.get('telefoon')
        email = request.form.get('email')

        # Update de leverancier
        cur.execute("""
            UPDATE leveranciers 
            SET naam = %s, contact = %s, telefoon = %s, email = %s
            WHERE leverancier_id = %s AND chef_id = %s
        """, (naam, contact, telefoon, email, leverancier_id, session['chef_id']))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        logger.error(f'Error updating supplier: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()
        conn.close()
