from flask import render_template, redirect, url_for, flash, request, session, jsonify, current_app
from . import bp
from utils.db import get_db_connection
from utils.auth_decorators import admin_required
from werkzeug.utils import secure_filename
import logging
import os

logger = logging.getLogger(__name__)

@bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard pagina"""
    return render_template('admin/dashboard.html')

@bp.route('/users')
@admin_required
def manage_users():
    """Beheer alle gebruikers"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Removed username column from the query since it doesn't exist
        cur.execute("SELECT chef_id, naam, email, is_admin FROM chefs ORDER BY naam")
        users = cur.fetchall()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers')
@admin_required
def manage_system_suppliers():
    """Beheer systeemleveranciers"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Fetch system suppliers
        cur.execute("""
            SELECT l.*, 
                   (SELECT COUNT(*) FROM system_ingredients WHERE leverancier_id = l.leverancier_id) as ingredient_count 
            FROM leveranciers l 
            WHERE l.is_admin_created = TRUE
        """)
        system_suppliers = cur.fetchall()
        
        # Fetch all chefs for the dropdown
        cur.execute("SELECT chef_id, naam FROM chefs ORDER BY naam")
        chefs = cur.fetchall()
        
        return render_template('admin/suppliers.html', 
                              suppliers=system_suppliers, 
                              chefs=chefs)
    except Exception as e:
        logger.error(f"Error fetching system suppliers: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/add', methods=['POST'])
@admin_required
def add_system_supplier():
    """Voeg een nieuwe systeemleverancier toe"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    
    cur = conn.cursor()
    
    try:
        naam = request.form.get('naam')
        contact = request.form.get('contact', '')
        telefoon = request.form.get('telefoon', '')
        email = request.form.get('email', '')
        
        if not naam:
            flash("Naam is verplicht.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        # Handle Excel file upload
        excel_file_path = None
        has_standard_list = False
        
        if 'excel_file' in request.files and request.files['excel_file'].filename:
            excel_file = request.files['excel_file']
            if excel_file.filename.lower().endswith(('.xlsx', '.xls')):
                try:
                    # Generate a safe filename
                    filename = secure_filename(f"{naam.replace(' ', '_')}_ingredienten.xlsx")
                    
                    # Use the app's storage system (S3 or local)
                    path = f"supplier_excel/{filename}"
                    current_app.storage.save_file(excel_file, path)
                    
                    excel_file_path = path
                    has_standard_list = True
                    
                except Exception as e:
                    logger.error(f"Error uploading Excel file: {str(e)}")
                    flash(f"Fout bij uploaden Excel bestand: {str(e)}", "warning")
            else:
                flash("Alleen Excel bestanden (xlsx, xls) zijn toegestaan", "warning")
        
        # Handle logo file upload
        logo_path = None
        if 'logo_file' in request.files and request.files['logo_file'].filename:
            logo_file = request.files['logo_file']
            if logo_file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                try:
                    # Generate a safe filename
                    filename = secure_filename(f"{naam.replace(' ', '_')}_logo{os.path.splitext(logo_file.filename)[1]}")
                    
                    # Use the app's storage system (S3 or local)
                    path = f"supplier_logos/{filename}"
                    current_app.storage.save_file(logo_file, path)
                    
                    logo_path = path
                    
                except Exception as e:
                    logger.error(f"Error uploading logo file: {str(e)}")
                    flash(f"Fout bij uploaden logo: {str(e)}", "warning")
            else:
                flash("Alleen afbeeldingsbestanden (jpg, jpeg, png, gif) zijn toegestaan voor het logo", "warning")
        
        # Systeemleverancier toevoegen met is_admin_created=TRUE
        cur.execute("""
            INSERT INTO leveranciers (naam, contact, telefoon, email, is_admin_created, excel_file_path, has_standard_list, logo_path) 
            VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s)
        """, (naam, contact, telefoon, email, excel_file_path, has_standard_list, logo_path))
        
        conn.commit()
        flash(f"Systeemleverancier '{naam}' succesvol toegevoegd!", "success")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding system supplier: {str(e)}")
        flash(f"Fout bij toevoegen van systeemleverancier: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin.manage_system_suppliers'))

@bp.route('/suppliers/<int:supplier_id>/update', methods=['POST'])
@admin_required
def update_system_supplier(supplier_id):
    """Update een bestaande systeemleverancier"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        naam = request.form.get('naam')
        contact = request.form.get('contact', '')
        telefoon = request.form.get('telefoon', '')
        email = request.form.get('email', '')
        
        if not naam:
            flash("Naam is verplicht.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        # Controleer eerst of dit een admin-gemaakte leverancier is
        cur.execute("SELECT is_admin_created, excel_file_path, logo_path FROM leveranciers WHERE leverancier_id = %s", (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier or not supplier.get('is_admin_created'):
            flash("Alleen systeemleveranciers kunnen hier worden bewerkt.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        # Handle Excel file upload
        excel_file_path = supplier.get('excel_file_path')  # Keep existing file by default
        has_standard_list = bool(excel_file_path)  # Keep existing status by default
        
        if 'excel_file' in request.files and request.files['excel_file'].filename:
            excel_file = request.files['excel_file']
            if excel_file.filename.lower().endswith(('.xlsx', '.xls')):
                try:
                    # Generate a safe filename
                    filename = secure_filename(f"{naam.replace(' ', '_')}_ingredienten.xlsx")
                    
                    # Use the app's storage system (S3 or local)
                    path = f"supplier_excel/{filename}"
                    
                    # Remove old file if it exists
                    if excel_file_path:
                        try:
                            current_app.storage.delete_file(excel_file_path)
                        except Exception as e:
                            logger.warning(f"Could not delete old Excel file: {str(e)}")
                    
                    current_app.storage.save_file(excel_file, path)
                    excel_file_path = path
                    has_standard_list = True
                    
                except Exception as e:
                    logger.error(f"Error uploading Excel file: {str(e)}")
                    flash(f"Fout bij uploaden Excel bestand: {str(e)}", "warning")
            else:
                flash("Alleen Excel bestanden (xlsx, xls) zijn toegestaan", "warning")
        
        # Handle excel file removal
        if request.form.get('remove_excel') == 'true' and excel_file_path:
            try:
                current_app.storage.delete_file(excel_file_path)
                excel_file_path = None
                has_standard_list = False
                flash("Excel bestand verwijderd.", "success")
            except Exception as e:
                logger.error(f"Error removing Excel file: {str(e)}")
                flash(f"Fout bij verwijderen Excel bestand: {str(e)}", "warning")
        
        # Handle logo file upload
        logo_path = supplier.get('logo_path')  # Keep existing logo by default
        
        if 'logo_file' in request.files and request.files['logo_file'].filename:
            logo_file = request.files['logo_file']
            if logo_file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                try:
                    # Generate a safe filename
                    filename = secure_filename(f"{naam.replace(' ', '_')}_logo{os.path.splitext(logo_file.filename)[1]}")
                    
                    # Use the app's storage system (S3 or local)
                    path = f"supplier_logos/{filename}"
                    
                    # Remove old file if it exists
                    if logo_path:
                        try:
                            current_app.storage.delete_file(logo_path)
                        except Exception as e:
                            logger.warning(f"Could not delete old logo file: {str(e)}")
                    
                    current_app.storage.save_file(logo_file, path)
                    logo_path = path
                    
                except Exception as e:
                    logger.error(f"Error uploading logo file: {str(e)}")
                    flash(f"Fout bij uploaden logo: {str(e)}", "warning")
            else:
                flash("Alleen afbeeldingsbestanden (jpg, jpeg, png, gif) zijn toegestaan voor het logo", "warning")
        
        # Handle logo removal
        if request.form.get('remove_logo') == 'true' and logo_path:
            try:
                current_app.storage.delete_file(logo_path)
                logo_path = None
                flash("Logo verwijderd.", "success")
            except Exception as e:
                logger.error(f"Error removing logo file: {str(e)}")
                flash(f"Fout bij verwijderen logo: {str(e)}", "warning")
        
        # Update de leverancier
        cur.execute("""
            UPDATE leveranciers 
            SET naam = %s, contact = %s, telefoon = %s, email = %s, excel_file_path = %s, 
                has_standard_list = %s, logo_path = %s
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (naam, contact, telefoon, email, excel_file_path, has_standard_list, logo_path, supplier_id))
        
        conn.commit()
        flash(f"Systeemleverancier succesvol bijgewerkt!", "success")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating system supplier: {str(e)}")
        flash(f"Fout bij bijwerken van systeemleverancier: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin.manage_system_suppliers'))

@bp.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
@admin_required
def delete_system_supplier(supplier_id):
    """Verwijder een systeemleverancier"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Controleer eerst of dit een admin-gemaakte leverancier is
        cur.execute("SELECT is_admin_created FROM leveranciers WHERE leverancier_id = %s", (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier or not supplier.get('is_admin_created'):
            return jsonify({'success': False, 'error': 'Alleen systeemleveranciers kunnen hier worden verwijderd'}), 403
        
        # Verwijder de leverancier
        cur.execute("DELETE FROM leveranciers WHERE leverancier_id = %s AND is_admin_created = TRUE", (supplier_id,))
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting system supplier: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@bp.route('/users/<int:chef_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_status(chef_id):
    """Toggle admin status for a user"""
    # Prevent self-demotion to maintain at least one admin
    if chef_id == session['chef_id']:
        return jsonify({'success': False, 'error': 'Je kunt je eigen admin status niet wijzigen'})
        
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'})
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # First get the current admin status
        cur.execute("SELECT is_admin FROM chefs WHERE chef_id = %s", (chef_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': 'Gebruiker niet gevonden'})
        
        # Toggle the admin status
        new_status = not user['is_admin']
        
        cur.execute("UPDATE chefs SET is_admin = %s WHERE chef_id = %s", 
                   (new_status, chef_id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        logger.error(f"Error toggling admin status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()
        conn.close()

@bp.route('/chef-suppliers')
@admin_required
def get_chef_suppliers():
    """Get suppliers for a specific chef"""
    chef_id = request.args.get('chef_id')
    if not chef_id:
        return jsonify({'success': False, 'error': 'Chef ID is required'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get all suppliers for this chef
        cur.execute("""
            SELECT l.*, 
                   (SELECT COUNT(*) FROM ingredients i WHERE i.leverancier_id = l.leverancier_id) AS ingredient_count
            FROM leveranciers l
            WHERE l.chef_id = %s AND l.is_admin_created = FALSE
            ORDER BY l.naam
        """, (chef_id,))
        
        suppliers = cur.fetchall()
        return jsonify({'success': True, 'suppliers': suppliers})
    except Exception as e:
        logger.error(f"Error fetching chef suppliers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@bp.route('/supplier-ingredients')
@admin_required
def get_supplier_ingredients():
    """Get ingredients for a specific supplier"""
    supplier_id = request.args.get('supplier_id')
    if not supplier_id:
        return jsonify({'success': False, 'error': 'Supplier ID is required'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Check if this is a chef's supplier or system supplier
        cur.execute("""
            SELECT is_admin_created FROM leveranciers 
            WHERE leverancier_id = %s
        """, (supplier_id,))
        
        supplier = cur.fetchone()
        if not supplier:
            return jsonify({'success': False, 'error': 'Supplier not found'})
        
        if supplier['is_admin_created']:
            # Get system ingredients
            cur.execute("""
                SELECT * FROM system_ingredients
                WHERE leverancier_id = %s
            """, (supplier_id,))
        else:
            # Get chef's ingredients
            cur.execute("""
                SELECT * FROM ingredients
                WHERE leverancier_id = %s
            """, (supplier_id,))
        
        ingredients = cur.fetchall()
        return jsonify({'success': True, 'ingredients': ingredients})
    except Exception as e:
        logger.error(f"Error fetching supplier ingredients: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@bp.route('/promote-supplier', methods=['POST'])
@admin_required
def promote_supplier_to_system():
    """Promote a regular supplier to a system supplier"""
    data = request.json
    supplier_id = data.get('leverancier_id')
    
    if not supplier_id:
        return jsonify({'success': False, 'error': 'Supplier ID is required'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Start transaction
        conn.start_transaction()
        
        # Get the supplier info
        cur.execute("""
            SELECT * FROM leveranciers
            WHERE leverancier_id = %s
        """, (supplier_id,))
        
        supplier = cur.fetchone()
        if not supplier:
            return jsonify({'success': False, 'error': 'Supplier not found'}), 404
        
        # Create a new system supplier
        cur.execute("""
            INSERT INTO leveranciers (naam, contact, telefoon, email, is_admin_created)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (supplier['naam'], supplier['contact'], supplier['telefoon'], supplier['email']))
        
        new_supplier_id = cur.lastrowid
        
        # Get all ingredients for this supplier
        cur.execute("""
            SELECT * FROM ingredients
            WHERE leverancier_id = %s
        """, (supplier_id,))
        
        ingredients = cur.fetchall()
        
        # Create system ingredients - these won't be tied to a chef
        # They will be imported by chefs when importing the supplier
        system_ingredients_count = 0
        for ingredient in ingredients:
            cur.execute("""
                INSERT INTO system_ingredients (
                    leverancier_id, naam, eenheid, 
                    prijs_per_eenheid, categorie
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                new_supplier_id,
                ingredient['naam'],
                ingredient['eenheid'],
                ingredient['prijs_per_eenheid'],
                ingredient['categorie']
            ))
            system_ingredients_count += 1
        
        conn.commit()
        return jsonify({
            'success': True, 
            'message': f'Supplier promoted successfully with {system_ingredients_count} ingredients',
            'ingredient_count': system_ingredients_count
        })
    except Exception as e:
        conn.rollback()
        logger.error(f"Error promoting supplier: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/ingredients', methods=['GET', 'POST'])
@admin_required
def manage_system_ingredients(supplier_id):
    """Beheer ingrediënten van een systeemleverancier"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Check if this is a system supplier
        cur.execute("""
            SELECT * FROM leveranciers
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        
        supplier = cur.fetchone()
        if not supplier:
            flash("Alleen systeemleveranciers kunnen hier worden bewerkt.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        # Handle form submission for adding new ingredient
        if request.method == 'POST':
            naam = request.form.get('naam')
            categorie = request.form.get('categorie', '')
            eenheid = request.form.get('eenheid', '')
            prijs_per_eenheid = request.form.get('prijs_per_eenheid', 0)
            
            # Basic validation
            if not naam:
                flash("Naam is verplicht.", "danger")
            else:
                # Add the ingredient
                try:
                    cur.execute("""
                        INSERT INTO system_ingredients 
                        (leverancier_id, naam, categorie, eenheid, prijs_per_eenheid)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (supplier_id, naam, categorie, eenheid, prijs_per_eenheid))
                    
                    conn.commit()
                    flash(f"Ingredient '{naam}' succesvol toegevoegd!", "success")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error adding system ingredient: {str(e)}")
                    flash(f"Fout bij toevoegen ingredient: {str(e)}", "danger")
        
        # Get all ingredients for this supplier
        cur.execute("""
            SELECT * FROM system_ingredients
            WHERE leverancier_id = %s
            ORDER BY naam
        """, (supplier_id,))
        
        ingredients = cur.fetchall()
        
        return render_template('admin/system_ingredients.html', 
                               supplier=supplier,
                               ingredients=ingredients)
    except Exception as e:
        logger.error(f"Error managing system ingredients: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/ingredients/<int:ingredient_id>/delete', methods=['POST'])
@admin_required
def delete_system_ingredient(supplier_id, ingredient_id):
    """Verwijder een ingredient van een systeemleverancier"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500
    
    cur = conn.cursor()
    
    try:
        # Verify this is a system supplier
        cur.execute("""
            SELECT is_admin_created FROM leveranciers 
            WHERE leverancier_id = %s
        """, (supplier_id,))
        
        supplier = cur.fetchone()
        if not supplier or not supplier[0]:
            return jsonify({'success': False, 'error': 'Alleen ingrediënten van systeemleveranciers kunnen hier worden verwijderd'}), 403
        
        # Delete the ingredient
        cur.execute("""
            DELETE FROM system_ingredients
            WHERE system_ingredient_id = %s AND leverancier_id = %s
        """, (ingredient_id, supplier_id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting system ingredient: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/process-excel', methods=['POST'])
@admin_required
def process_supplier_excel(supplier_id):
    """Process the Excel file for a system supplier and add ingredients"""
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("SELECT * FROM leveranciers WHERE leverancier_id = %s AND is_admin_created = TRUE", (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            flash("Systeemleverancier niet gevonden.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        if not supplier.get('excel_file_path'):
            flash("Deze leverancier heeft geen Excel bestand.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        # Log the file path for debugging
        file_path = supplier.get('excel_file_path')
        logger.info(f"Attempting to retrieve Excel file from path: {file_path}")
        
        # Get the Excel file from S3 or local storage
        try:
            import pandas as pd
            import io
            import boto3
            from botocore.exceptions import ClientError
            
            if current_app.config.get('USE_S3'):
                # Get file from S3
                s3_client = boto3.client(
                    's3',
                    region_name='eu-central-1',
                    aws_access_key_id=current_app.config.get('S3_KEY'),
                    aws_secret_access_key=current_app.config.get('S3_SECRET')
                )
                
                try:
                    logger.debug(f"Retrieving file from S3: {file_path}")
                    
                    # Log S3 configuration for debugging
                    bucket = current_app.config.get('S3_BUCKET')
                    logger.info(f"Using S3 bucket: {bucket}")
                    
                    try:
                        # First check if the file exists in S3
                        s3_client.head_object(Bucket=bucket, Key=file_path)
                        logger.info(f"File exists in S3: {file_path}")
                    except ClientError as e:
                        if e.response['Error']['Code'] == '404':
                            # REDIRECT TO THE RECOVERY PAGE instead of showing an error
                            return redirect(url_for('admin.recover_missing_excel', supplier_id=supplier_id, 
                                                    file_path=file_path))
                        else:
                            raise
                            
                    # Now try to get the file content
                    response = s3_client.get_object(
                        Bucket=bucket,
                        Key=file_path
                    )
                    
                    # Read content to a buffer pandas can read
                    content = response['Body'].read()
                    excel_buffer = io.BytesIO(content)
                    
                    # Read Excel file with pandas
                    df = pd.read_excel(excel_buffer)
                    
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = e.response.get('Error', {}).get('Message', str(e))
                    
                    logger.error(f"S3 Error ({error_code}): {error_msg}")
                    logger.error(f"S3 Configuration - Bucket: {current_app.config.get('S3_BUCKET')}, Has Key: {bool(current_app.config.get('S3_KEY'))}, Has Secret: {bool(current_app.config.get('S3_SECRET'))}")
                    
                    # REDIRECT TO THE RECOVERY PAGE for any other S3 errors
                    return redirect(url_for('admin.recover_missing_excel', supplier_id=supplier_id, 
                                           file_path=file_path))
            else:
                # Get file from local storage
                local_path = os.path.join(current_app.root_path, 'static', file_path)
                if not os.path.exists(local_path):
                    flash(f"Excel bestand niet gevonden op de server. Pad: {local_path}", "danger")
                    return redirect(url_for('admin.manage_system_suppliers'))
                
                # Read Excel file with pandas
                df = pd.read_excel(local_path)
            
            # Process the Excel data
            if df is None or df.empty:
                flash("Excel bestand is leeg of kon niet worden gelezen.", "danger")
                return redirect(url_for('admin.manage_system_suppliers'))
            
            # Check required columns: naam, categorie, eenheid, prijs_per_eenheid
            required_columns = ['naam', 'categorie', 'eenheid', 'prijs_per_eenheid']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                flash(f"Excel bestand mist verplichte kolommen: {', '.join(missing_cols)}", "danger")
                return redirect(url_for('admin.manage_system_suppliers'))
            
            # First, delete existing ingredients for this supplier
            cur.execute("DELETE FROM system_ingredients WHERE leverancier_id = %s", (supplier_id,))
            
            # Process each row and create system_ingredients
            successful_count = 0
            failed_rows = []
            
            for _, row in df.iterrows():
                try:
                    # Extract values with error handling for missing or invalid data
                    naam = str(row['naam']) if not pd.isna(row['naam']) else None
                    if not naam:
                        failed_rows.append(f"Rij {_ + 2}: Naam is verplicht")
                        continue
                        
                    categorie = str(row['categorie']) if not pd.isna(row['categorie']) else ''
                    eenheid = str(row['eenheid']) if not pd.isna(row['eenheid']) else ''
                    
                    # Handle price as float
                    try:
                        prijs = float(row['prijs_per_eenheid']) if not pd.isna(row['prijs_per_eenheid']) else 0.0
                    except (ValueError, TypeError):
                        prijs = 0.0
                    
                    # Insert into system_ingredients with only needed columns
                    cur.execute("""
                        INSERT INTO system_ingredients (
                            leverancier_id, naam, categorie, eenheid, prijs_per_eenheid
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        supplier_id, naam, categorie, eenheid, prijs
                    ))
                    
                    successful_count += 1
                    
                except Exception as e:
                    failed_rows.append(f"Rij {_ + 2}: {str(e)}")
            
            conn.commit()
            
            if failed_rows:
                flash_message = f"{successful_count} ingrediënten succesvol toegevoegd. {len(failed_rows)} rijen overgeslagen."
                flash(flash_message, "warning")
                for err in failed_rows[:5]:  # Show only first 5 errors
                    flash(err, "warning")
                if len(failed_rows) > 5:
                    flash(f"... en {len(failed_rows) - 5} meer fouten.", "warning")
            else:
                flash(f"{successful_count} ingrediënten succesvol toegevoegd aan systeemleverancier '{supplier['naam']}'.", "success")
                
            return redirect(url_for('admin.manage_system_ingredients', supplier_id=supplier_id))
            
        except Exception as e:
            logger.error(f"Error processing Excel: {str(e)}", exc_info=True)
            flash(f"Fout bij verwerken Excel bestand: {str(e)}", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error processing supplier Excel: {str(e)}")
        flash(f"Fout bij verwerken van Excel bestand: {str(e)}", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/recover-excel', methods=['GET', 'POST'])
@admin_required
def recover_missing_excel(supplier_id):
    """Recovery page for missing Excel files"""
    file_path = request.args.get('file_path', '')
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("SELECT * FROM leveranciers WHERE leverancier_id = %s AND is_admin_created = TRUE", (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            flash("Systeemleverancier niet gevonden.", "danger")
            return redirect(url_for('admin.manage_system_suppliers'))
        
        if request.method == 'POST':
            # Handle the uploaded Excel file
            if 'excel_file' not in request.files:
                flash("Geen bestand geüpload.", "danger")
                return redirect(request.url)
            
            excel_file = request.files['excel_file']
            
            if excel_file.filename == '':
                flash("Geen bestand geselecteerd.", "danger")
                return redirect(request.url)
            
            if excel_file and excel_file.filename.lower().endswith(('.xlsx', '.xls')):
                try:
                    # Use either the original path or create a new one
                    if file_path and supplier['excel_file_path'] == file_path:
                        path = file_path
                    else:
                        # Generate a safe filename
                        filename = secure_filename(f"{supplier['naam'].replace(' ', '_')}_ingredienten.xlsx")
                        path = f"supplier_excel/{filename}"
                    
                    # Save the file to S3 or local storage
                    current_app.storage.save_file(excel_file, path)
                    
                    # Update the supplier's excel_file_path if it's different
                    if path != supplier.get('excel_file_path'):
                        cur.execute("""
                            UPDATE leveranciers 
                            SET excel_file_path = %s, has_standard_list = TRUE
                            WHERE leverancier_id = %s
                        """, (path, supplier_id))
                        conn.commit()
                    
                    flash("Excel bestand succesvol hersteld! Je kunt nu het bestand verwerken.", "success")
                    return redirect(url_for('admin.manage_system_ingredients', supplier_id=supplier_id))
                    
                except Exception as e:
                    logger.error(f"Error uploading Excel file: {str(e)}")
                    flash(f"Fout bij uploaden Excel bestand: {str(e)}", "danger")
            else:
                flash("Alleen Excel bestanden (xlsx, xls) zijn toegestaan.", "danger")
        
        return render_template('admin/recover_excel.html', 
                              supplier=supplier,
                              file_path=file_path)
    except Exception as e:
        logger.error(f"Error in recover_missing_excel: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.manage_system_suppliers'))
    finally:
        cur.close()
        conn.close()