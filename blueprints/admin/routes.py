from flask import render_template, redirect, url_for, flash, request, session, jsonify, current_app, send_file
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from utils.db import get_db_connection
from . import bp
import logging
import os
import datetime
import boto3  # Add this import for AWS S3 operations
from botocore.exceptions import ClientError  # Also add this for better error handling

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
    if (form.validate_on_submit()):
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
        
        # NIEUW: Verwijder password_resets records
        cur.execute("DELETE FROM password_resets WHERE chef_id = %s", (chef_id,))
        
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

@bp.route('/suppliers')
@admin_required
def manage_suppliers():
    """Admin supplier management page"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.dashboard'))
        
    cur = conn.cursor(dictionary=True)
    try:
        # Retrieve all admin-created suppliers
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE is_admin_created = TRUE
            ORDER BY naam
        """)
        suppliers = cur.fetchall()
        
        return render_template('admin/suppliers.html', suppliers=suppliers)
    except Exception as e:
        logger.error(f"Admin suppliers error: {str(e)}")
        flash("Er is een fout opgetreden bij het laden van leveranciers", "danger")
        return redirect(url_for('admin.dashboard'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/create', methods=['GET', 'POST'])
@admin_required
def create_supplier():
    """Create a new admin supplier"""
    if request.method == 'POST':
        # Get form data
        naam = request.form.get('naam')
        contact = request.form.get('contact')
        telefoon = request.form.get('telefoon')
        email = request.form.get('email')
        has_standard_list = bool(request.form.get('has_standard_list'))
        
        # Handle banner image upload
        banner_image = None
        if 'banner_image' in request.files and request.files['banner_image'].filename:
            file = request.files['banner_image']
            if file:
                # Use our storage utility instead of direct filesystem operations
                banner_image = current_app.storage.save_file(
                    file, 
                    'uploads/banners'
                )
        
        # Handle CSV file upload
        csv_file_path = None
        if 'ingredients_csv' in request.files and request.files['ingredients_csv'].filename:
            file = request.files['ingredients_csv']
            if file:
                # Use our storage utility
                csv_file_path = current_app.storage.save_file(
                    file,
                    'uploads/ingredient_lists'
                )
        
        conn = get_db_connection()
        if not conn:
            flash("Database verbinding mislukt", "danger")
            return redirect(url_for('admin.manage_suppliers'))
        
        cur = conn.cursor()
        try:
            # Insert new supplier with CSV file path
            cur.execute("""
                INSERT INTO leveranciers 
                (naam, contact, telefoon, email, banner_image, is_admin_created, has_standard_list, chef_id, csv_file_path, csv_last_updated)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, NULL, %s, %s)
            """, (naam, contact, telefoon, email, banner_image, has_standard_list, csv_file_path, 
                 datetime.datetime.now() if csv_file_path else None))
            
            conn.commit()
            flash("Leverancier succesvol aangemaakt!", "success")
            return redirect(url_for('admin.manage_suppliers'))
        except Exception as e:
            conn.rollback()
            logger.error(f"Create supplier error: {str(e)}")
            flash(f"Er is een fout opgetreden bij het aanmaken van de leverancier: {str(e)}", "danger")
            return redirect(url_for('admin.manage_suppliers'))
        finally:
            cur.close()
            conn.close()
            
    # GET request: render form
    return render_template('admin/create_supplier.html')

@bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_supplier(supplier_id):
    """Edit an admin supplier"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.manage_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            flash("Leverancier niet gevonden", "danger")
            return redirect(url_for('admin.manage_suppliers'))
        
        if request.method == 'POST':
            # Get form data
            naam = request.form.get('naam')
            contact = request.form.get('contact')
            telefoon = request.form.get('telefoon')
            email = request.form.get('email')
            has_standard_list = bool(request.form.get('has_standard_list'))
            
            # Handle banner image upload
            banner_image = supplier['banner_image']
            if 'banner_image' in request.files and request.files['banner_image'].filename:
                file = request.files['banner_image']
                if file:
                    # Delete old banner if exists
                    if banner_image:
                        current_app.storage.delete_file(banner_image)
                    
                    # Upload new banner
                    banner_image = current_app.storage.save_file(
                        file,
                        'uploads/banners'
                    )
            
            # Handle CSV file upload
            csv_file_path = supplier['csv_file_path']
            csv_updated = False
            if 'ingredients_csv' in request.files and request.files['ingredients_csv'].filename:
                file = request.files['ingredients_csv']
                if file:
                    # Delete old CSV if exists
                    if csv_file_path:
                        current_app.storage.delete_file(csv_file_path)
                    
                    # Upload new CSV
                    csv_file_path = current_app.storage.save_file(
                        file, 
                        'uploads/ingredient_lists'
                    )
                    csv_updated = True
            
            # Update supplier
            cur.execute("""
                UPDATE leveranciers 
                SET naam = %s, contact = %s, telefoon = %s, email = %s, 
                    banner_image = %s, has_standard_list = %s, csv_file_path = %s,
                    csv_last_updated = %s
                WHERE leverancier_id = %s
            """, (naam, contact, telefoon, email, banner_image, has_standard_list, 
                  csv_file_path, datetime.datetime.now() if csv_updated else supplier['csv_last_updated'], 
                  supplier_id))
            
            conn.commit()
            flash("Leverancier succesvol bijgewerkt!", "success")
            return redirect(url_for('admin.manage_suppliers'))
            
        return render_template('admin/edit_supplier.html', supplier=supplier)
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Edit supplier error: {str(e)}")
        flash(f"Er is een fout opgetreden bij het bewerken van de leverancier: {str(e)}", "danger")
        return redirect(url_for('admin.manage_suppliers'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
@admin_required
def delete_supplier(supplier_id):
    """Delete an admin supplier"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.manage_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Check if supplier exists and is admin-created
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        
        supplier = cur.fetchone()
        if not supplier:
            flash("Leverancier niet gevonden of geen admin leverancier", "danger")
            return redirect(url_for('admin.manage_suppliers'))
        
        # Delete supplier
        cur.execute("DELETE FROM leveranciers WHERE leverancier_id = %s", (supplier_id,))
        conn.commit()
        
        # Remove banner image if it exists
        if supplier['banner_image']:
            banner_path = os.path.join(current_app.root_path, 'static', supplier['banner_image'])
            if os.path.exists(banner_path):
                os.remove(banner_path)
        
        flash("Leverancier succesvol verwijderd!", "success")
        return redirect(url_for('admin.manage_suppliers'))
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Delete supplier error: {str(e)}")
        flash(f"Er is een fout opgetreden bij het verwijderen van de leverancier: {str(e)}", "danger")
        return redirect(url_for('admin.manage_suppliers'))
    finally:
        cur.close()
        conn.close()

@bp.route('/suppliers/<int:supplier_id>/delete-csv', methods=['POST'])
@admin_required
def delete_supplier_csv(supplier_id):
    """Delete the CSV file from a supplier"""
    logger.info(f"Attempting to delete CSV for supplier ID: {supplier_id}")
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        if is_ajax:
            return jsonify({"success": False, "error": "Database verbinding mislukt"}), 500
        else:
            flash("Database verbinding mislukt", "danger")
            return redirect(url_for('admin.manage_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            logger.warning(f"Supplier {supplier_id} not found")
            if is_ajax:
                return jsonify({"success": False, "error": "Leverancier niet gevonden"}), 404
            else:
                flash("Leverancier niet gevonden", "danger")
                return redirect(url_for('admin.manage_suppliers'))
        
        if not supplier['csv_file_path']:
            logger.warning(f"Supplier {supplier_id} has no CSV file path")
            if is_ajax:
                return jsonify({"success": False, "error": "Deze leverancier heeft geen CSV bestand"}), 400
            else:
                flash("Deze leverancier heeft geen CSV bestand", "warning")
                return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))
        
        # Log the CSV file path we're trying to delete
        csv_path = supplier['csv_file_path']
        
        # Normalize the path to ensure consistent format
        csv_path = csv_path.strip().replace('\\', '/')
        if csv_path.startswith('/'):
            csv_path = csv_path[1:]
            
        logger.info(f"Normalized CSV file path: {csv_path}")
        
        # Initialize deletion status
        file_deleted = False
        
        # ALWAYS try direct S3 deletion first regardless of storage mode setting
        # This ensures we handle S3 files correctly even if config is inconsistent
        try:
            s3_bucket = current_app.config.get('S3_BUCKET')
            s3_key = current_app.config.get('S3_KEY')
            s3_secret = current_app.config.get('S3_SECRET')
            
            if s3_bucket and s3_key and s3_secret:
                logger.info(f"Attempting direct S3 deletion with bucket: {s3_bucket}")
                
                # Create direct S3 client
                s3_client = boto3.client(
                    's3',
                    region_name='eu-west-1',
                    aws_access_key_id=s3_key,
                    aws_secret_access_key=s3_secret,
                    config=boto3.session.Config(signature_version='s3v4')
                )
                
                # Check if the file exists first
                try:
                    s3_client.head_object(Bucket=s3_bucket, Key=csv_path)
                    logger.info(f"File exists in S3, proceeding with deletion")
                    
                    # Delete the file
                    s3_client.delete_object(
                        Bucket=s3_bucket,
                        Key=csv_path
                    )
                    
                    # Verify the deletion worked
                    try:
                        s3_client.head_object(Bucket=s3_bucket, Key=csv_path)
                        logger.error("File still exists after deletion attempt!")
                        file_deleted = False
                    except ClientError as e:
                        if e.response['Error']['Code'] == '404':
                            logger.info("Verified file is deleted from S3")
                            file_deleted = True
                        else:
                            logger.error(f"Error verifying deletion: {str(e)}")
                            file_deleted = False
                            
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        logger.warning(f"File not found in S3: {csv_path}")
                        # Still proceed with database update
                        file_deleted = True
                    else:
                        logger.error(f"Error checking if file exists: {str(e)}")
            else:
                logger.warning("S3 credentials not found in config")
        except Exception as e:
            logger.error(f"Direct S3 deletion attempt failed: {str(e)}")
        
        # As a fallback, try using the storage utility
        if not file_deleted:
            logger.info("Trying deletion via storage utility as fallback")
            file_deleted = current_app.storage.delete_file(csv_path)
            logger.info(f"Storage utility deletion result: {file_deleted}")
        
        # Update database regardless of file deletion success
        # This ensures the UI is consistent even if file deletion has issues
        cur.execute("""
            UPDATE leveranciers 
            SET csv_file_path = NULL, csv_last_updated = NULL
            WHERE leverancier_id = %s
        """, (supplier_id,))
        
        conn.commit()
        logger.info("Database updated successfully")
        
        success_message = "CSV bestand succesvol verwijderd"
        warning_message = "CSV verwijzing verwijderd uit database, maar er was een fout bij het verwijderen van het bestand zelf. Dit wordt automatisch opgelost bij de volgende systeem opschoning."
        
        if is_ajax:
            return jsonify({
                "success": True,
                "message": success_message if file_deleted else warning_message,
                "file_deleted": file_deleted
            })
        else:
            if file_deleted:
                flash(success_message, "success")
            else:
                flash(warning_message, "warning")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in delete_supplier_csv: {str(e)}", exc_info=True)
        if is_ajax:
            return jsonify({"success": False, "error": f"Er is een fout opgetreden: {str(e)}"}), 500
        else:
            flash(f"Er is een fout opgetreden bij het verwijderen van het CSV bestand: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    
    if not is_ajax:
        return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))

@bp.route('/suppliers/<int:supplier_id>/download-csv', methods=['GET'])
@admin_required
def download_supplier_csv(supplier_id):
    """Download the CSV file from a supplier"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.manage_suppliers'))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE
        """, (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            flash("Leverancier niet gevonden", "danger")
            return redirect(url_for('admin.manage_suppliers'))
        
        if not supplier['csv_file_path']:
            flash("Deze leverancier heeft geen CSV bestand", "warning")
            return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))
        
        # For S3 storage in production
        if current_app.config.get('USE_S3'):
            try:
                # Generate a pre-signed URL for temporary access
                url = current_app.storage.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': current_app.config['S3_BUCKET'],
                        'Key': supplier['csv_file_path']
                    },
                    ExpiresIn=60  # URL expires in 60 seconds
                )
                return redirect(url)
            except Exception as e:
                logger.error(f"Error generating S3 download URL: {str(e)}")
                flash(f"Er is een fout opgetreden bij het downloaden van het CSV bestand", "danger")
                return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))
        else:
            # Local file handling (existing code)
            csv_path = os.path.join(current_app.root_path, 'static', supplier['csv_file_path'])
            if not os.path.exists(csv_path):
                flash("CSV bestand niet gevonden op de server", "danger")
                return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))
            
            # Get filename from path
            filename = os.path.basename(csv_path)
            
            return send_file(
                csv_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        
    except Exception as e:
        logger.error(f"Download supplier CSV error: {str(e)}")
        flash(f"Er is een fout opgetreden bij het downloaden van het CSV bestand: {str(e)}", "danger")
        return redirect(url_for('admin.edit_supplier', supplier_id=supplier_id))
    finally:
        cur.close()
        conn.close()

@bp.route('/debug/files')
@admin_required
def debug_files():
    """Debug endpoint to display file URLs"""
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('admin.dashboard'))
        
    cur = conn.cursor(dictionary=True)
    try:
        # Get all suppliers with files
        cur.execute("""
            SELECT leverancier_id, naam, banner_image, csv_file_path 
            FROM leveranciers 
            WHERE banner_image IS NOT NULL OR csv_file_path IS NOT NULL
        """)
        suppliers = cur.fetchall()
        
        # Add URLs for debugging
        for supplier in suppliers:
            if supplier['banner_image']:
                supplier['banner_url'] = current_app.storage.get_file_url(supplier['banner_image'])
            if supplier['csv_file_path']:
                supplier['csv_url'] = current_app.storage.get_file_url(supplier['csv_file_path'])
        
        return render_template('admin/debug_files.html', suppliers=suppliers)
    except Exception as e:
        logger.error(f"Debug files error: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))
    finally:
        cur.close()
        conn.close()
