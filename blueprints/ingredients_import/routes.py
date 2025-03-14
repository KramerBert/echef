import os
import io
from flask import render_template, redirect, url_for, flash, request, session, current_app, send_file, jsonify
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm  # Add missing import
from flask_wtf.file import FileField, FileRequired, FileAllowed  # Add missing imports
from . import bp
from utils.db import get_db_connection
import logging
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from mysql.connector import Error
from markupsafe import Markup
import pandas as pd  # Make sure pandas is imported for Excel handling

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

@bp.route('/dashboard/<chef_naam>/import-ingredients', methods=['GET', 'POST'])
def import_ingredients(chef_naam):
    if session.get('chef_naam') != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    
    class UploadForm(FlaskForm):
        file = FileField('Excel bestand', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'xls'], 'Alleen Excel bestanden toegestaan!')
        ])
    
    form = UploadForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Get the uploaded file
            excel_file = form.file.data
            
            # Read Excel data
            df = pd.read_excel(excel_file)
            
            # Ensure the required columns are present
            required_columns = ['naam', 'eenheid', 'prijs_per_eenheid', 'categorie']
            if not all(col in df.columns for col in required_columns):
                flash("Excel bestand moet de kolommen 'naam', 'eenheid', 'prijs_per_eenheid' en 'categorie' bevatten.", "danger")
                return redirect(request.url)
            
            # Process the data
            conn = get_db_connection()
            if conn is None:
                flash("Database verbinding mislukt.", "danger")
                return redirect(url_for('dashboard', chef_naam=chef_naam))
            
            cur = conn.cursor()
            
            # Track which ingredients were skipped due to missing supplier
            skipped_ingredients = []
            imported_count = 0
            
            for _, row in df.iterrows():
                naam = row['naam']
                eenheid = row['eenheid']
                prijs_per_eenheid = row['prijs_per_eenheid']
                categorie = row['categorie']
                
                # Handle optional leverancier field
                leverancier_id = None
                leverancier_naam = row.get('leverancier')
                
                if pd.notna(leverancier_naam) and leverancier_naam.strip():
                    # Check if this supplier exists
                    cur.execute("""
                        SELECT leverancier_id FROM leveranciers
                        WHERE chef_id = %s AND naam = %s
                    """, (session['chef_id'], leverancier_naam))
                    
                    supplier_result = cur.fetchone()
                    if supplier_result:
                        leverancier_id = supplier_result[0]
                    else:
                        # Skip this ingredient and track it
                        skipped_ingredients.append({
                            'naam': naam,
                            'leverancier': leverancier_naam
                        })
                        continue
                
                # Insert the ingredient
                try:
                    cur.execute("""
                        INSERT INTO ingredients 
                        (chef_id, naam, eenheid, prijs_per_eenheid, categorie, leverancier_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (session['chef_id'], naam, eenheid, prijs_per_eenheid, categorie, leverancier_id))
                    imported_count += 1
                except Exception as e:
                    # Log the error but continue with other ingredients
                    print(f"Error importing ingredient {naam}: {str(e)}")
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Store skipped ingredients in session if any
            if skipped_ingredients:
                session['skipped_ingredients'] = skipped_ingredients
                flash(f"{len(skipped_ingredients)} ingrediënten overgeslagen vanwege onbekende leveranciers.", "warning")
            
            flash(f"{imported_count} ingrediënten succesvol geïmporteerd!", "success")
            return redirect(url_for('ingredients_bp.manage_ingredients', chef_naam=chef_naam))
            
        except Exception as e:
            flash(f"Fout bij importeren: {str(e)}", "danger")
            return redirect(request.url)
    
    return render_template('import_ingredients.html', chef_naam=chef_naam, form=form)

@bp.route('/from-supplier/<int:supplier_id>', methods=['POST'])
@login_required
def import_from_supplier(supplier_id):
    """Import ingredients from a supplier's standard list"""
    chef_id = session.get('chef_id')
    chef_naam = session.get('chef_naam')
    
    if not chef_id:
        flash("Je bent niet ingelogd als chef", "danger")
        return redirect(url_for('login'))
    
    # Check if we want to update existing ingredients
    update_existing = request.form.get('update_existing') == 'on'
    
    conn = get_db_connection()
    if not conn:
        flash("Database verbinding mislukt", "danger")
        return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Get supplier information
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE leverancier_id = %s AND is_admin_created = TRUE AND has_standard_list = TRUE
        """, (supplier_id,))
        supplier = cur.fetchone()
        
        if not supplier:
            flash("Deze leverancier heeft geen standaard ingrediëntenlijst", "danger")
            return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
        
        # Get the Excel file path - updated from CSV to Excel
        excel_path = supplier.get('excel_file_path')
        
        if not excel_path:
            flash("Geen Excel-bestand geconfigureerd voor deze leverancier", "danger")
            return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
        
        logger.info(f"Processing Excel from path: {excel_path}")
        
        try:
            # Check if using S3 storage
            if current_app.config.get('USE_S3'):
                # Get file from S3
                s3_client = boto3.client(
                    's3',
                    region_name='eu-central-1',
                    aws_access_key_id=current_app.config.get('S3_KEY'),
                    aws_secret_access_key=current_app.config.get('S3_SECRET')
                )
                
                try:
                    # Get the Excel file content
                    logger.debug(f"Retrieving file from S3: {excel_path}")
                    response = s3_client.get_object(
                        Bucket=current_app.config.get('S3_BUCKET'),
                        Key=excel_path
                    )
                    
                    # Save content to a temporary file that pandas can read
                    content = response['Body'].read()
                    temp_file = io.BytesIO(content)
                    
                    # Read Excel file with pandas
                    df = pd.read_excel(temp_file)
                    
                except ClientError as e:
                    logger.error(f"Error retrieving Excel from S3: {str(e)}")
                    flash(f"Fout bij ophalen bestand: {str(e)}", "danger")
                    return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
            else:
                # Get file from local storage
                local_path = os.path.join(current_app.root_path, 'static', excel_path)
                if os.path.exists(local_path):
                    # Read Excel file with pandas
                    df = pd.read_excel(local_path)
                else:
                    logger.error(f"Local Excel file not found: {local_path}")
                    flash("Excel bestand niet gevonden op de server", "danger")
                    return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
            
            # Process Excel data
            if df is not None:
                # Process dataframe to import ingredients
                result = process_excel_data(df, chef_id, supplier, update_existing)
                
                if result['success']:
                    skipped_ingredients = result['skipped_ingredients']
                    # Store skipped ingredients in session for display
                    if skipped_ingredients:
                        session['skipped_ingredients'] = skipped_ingredients
                        flash_msg = f"Succesvol {result['imported']} ingrediënten geïmporteerd van {supplier['naam']}. "
                        flash_msg += f"<a href='#' data-bs-toggle='modal' data-bs-target='#skippedIngredientsModal' class='alert-link'>"
                        flash_msg += f"{result['skipped']} ingrediënten overgeslagen (klik voor details)</a>."
                        flash(Markup(flash_msg), "success")  # Use Markup to prevent HTML escaping
                    else:
                        flash(f"Succesvol {result['imported']} ingrediënten geïmporteerd van {supplier['naam']}.", "success")
                else:
                    flash(f"Fout bij importeren: {result['error']}", "danger")
            else:
                flash("Kon Excel-bestand niet verwerken", "danger")
                
        except Exception as e:
            logger.error(f"Error processing Excel: {str(e)}", exc_info=True)
            flash(f"Fout bij verwerken bestand: {str(e)}", "danger")
        
        return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Import ingredients error: {str(e)}", exc_info=True)
        flash(f"Er is een fout opgetreden bij het importeren: {str(e)}", "danger")
        return redirect(url_for('suppliers.manage_suppliers', chef_naam=chef_naam))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def process_excel_data(df, chef_id, default_supplier=None, update_existing=False):
    """
    Process Excel data to import ingredients
    
    Args:
        df: Pandas DataFrame containing Excel data
        chef_id: ID of the chef
        default_supplier: Supplier info to use as default
        update_existing: Whether to update existing ingredients
        
    Returns:
        dict with results
    """
    logger.info(f"Processing Excel data with {len(df)} rows")
    result = {
        'success': False,
        'imported': 0,
        'skipped': 0,
        'skipped_ingredients': [],
        'error': None
    }
    
    try:
        # Get existing ingredients to avoid duplicates
        conn = get_db_connection()
        if not conn:
            result['error'] = "Database verbinding mislukt"
            return result
            
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT naam, ingredient_id FROM ingredients 
                WHERE chef_id = %s
            """, (chef_id,))
            existing_ingredients = {row['naam'].lower(): row['ingredient_id'] for row in cur.fetchall()}
            
            # Get categories and units
            categories = {}
            units = {}
            
            cur.execute("SELECT categorie_id, naam FROM categorieen WHERE chef_id = %s", (chef_id,))
            for row in cur.fetchall():
                categories[row['naam'].lower()] = row['categorie_id']
                
            cur.execute("SELECT eenheid_id, naam FROM eenheden WHERE chef_id = %s", (chef_id,))
            for row in cur.fetchall():
                units[row['naam'].lower()] = row['eenheid_id']
            
            # Process each row in the dataframe
            for _, row in df.iterrows():
                naam = row.get('naam') or row.get('ingredient') or row.get('name')
                
                if not naam or pd.isna(naam):
                    result['skipped'] += 1
                    continue
                
                naam = str(naam).strip()
                
                # Get category with fallback to "Overig"
                categorie = row.get('categorie') or row.get('category') or "Overig"
                categorie = str(categorie).strip() if not pd.isna(categorie) else "Overig"
                
                # Get unit with fallback to "stuk"
                eenheid = row.get('eenheid') or row.get('unit') or "stuk"
                eenheid = str(eenheid).strip() if not pd.isna(eenheid) else "stuk"
                
                # Get price with fallback to 0.0
                prijs = 0.0
                prijs_val = row.get('prijs_per_eenheid') or row.get('prijs') or row.get('price') or 0
                if not pd.isna(prijs_val):
                    try:
                        prijs = float(str(prijs_val).replace(',', '.'))
                    except ValueError:
                        prijs = 0.0
                
                # Get supplier name if available
                leverancier_naam = row.get('leverancier') or row.get('supplier')
                leverancier_id = default_supplier['leverancier_id'] if default_supplier else None
                
                if not pd.isna(leverancier_naam) and str(leverancier_naam).strip():
                    leverancier_naam = str(leverancier_naam).strip()
                    
                    # Try to find the supplier in the database
                    try:
                        cur.execute("""
                            SELECT leverancier_id FROM leveranciers 
                            WHERE LOWER(naam) = LOWER(%s) AND (chef_id = %s OR is_admin_created = TRUE)
                        """, (leverancier_naam, chef_id))
                        supplier_row = cur.fetchone()
                        
                        if supplier_row:
                            leverancier_id = supplier_row['leverancier_id']
                        elif leverancier_naam:  # Only create if not empty
                            # Create new supplier if it doesn't exist
                            cur.execute("""
                                INSERT INTO leveranciers (naam, chef_id) 
                                VALUES (%s, %s)
                            """, (leverancier_naam, chef_id))
                            leverancier_id = cur.lastrowid
                    except Exception as e:
                        logger.warning(f"Failed to process supplier {leverancier_naam}: {str(e)}")
                
                # Skip or update if ingredient with same name already exists
                if naam.lower() in existing_ingredients:
                    if update_existing:
                        try:
                            # Update existing ingredient
                            ingredient_id = existing_ingredients[naam.lower()]
                            cur.execute("""
                                UPDATE ingredients 
                                SET prijs_per_eenheid = %s,
                                    leverancier_id = %s
                                WHERE ingredient_id = %s
                            """, (prijs, leverancier_id, ingredient_id))
                            result['imported'] += 1
                        except Exception as e:
                            logger.warning(f"Failed to update ingredient {naam}: {str(e)}")
                            result['skipped'] += 1
                            result['skipped_ingredients'].append({
                                'naam': naam,
                                'reden': f'Fout bij bijwerken: {str(e)}'
                            })
                    else:
                        result['skipped'] += 1
                        result['skipped_ingredients'].append({
                            'naam': naam,
                            'reden': 'Ingredient bestaat al'
                        })
                    continue
                    
                # Add to existing ingredients dict to avoid duplicates in the import itself
                existing_ingredients[naam.lower()] = -1  # Placeholder ID
                
                # Get or create category
                category_id = None
                if categorie.lower() in categories:
                    category_id = categories[categorie.lower()]
                else:
                    try:
                        cur.execute("""
                            INSERT INTO categorieen (naam, chef_id) 
                            VALUES (%s, %s)
                        """, (categorie, chef_id))
                        category_id = cur.lastrowid
                        categories[categorie.lower()] = category_id
                    except Exception as e:
                        logger.warning(f"Failed to create category {categorie}: {str(e)}")
                
                # Get or create unit
                unit_id = None
                if eenheid.lower() in units:
                    unit_id = units[eenheid.lower()]
                else:
                    try:
                        cur.execute("""
                            INSERT INTO eenheden (naam, chef_id) 
                            VALUES (%s, %s)
                        """, (eenheid, chef_id))
                        unit_id = cur.lastrowid
                        units[eenheid.lower()] = unit_id
                    except Exception as e:
                        logger.warning(f"Failed to create unit {eenheid}: {str(e)}")
                
                # Insert the ingredient with category name
                try:
                    cur.execute("""
                        INSERT INTO ingredients 
                        (naam, categorie, eenheid, prijs_per_eenheid, leverancier_id, chef_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (naam, categorie, eenheid, prijs, leverancier_id, chef_id))
                    result['imported'] += 1
                except Exception as e:
                    logger.warning(f"Failed to insert ingredient {naam}: {str(e)}")
                    result['skipped'] += 1
                    result['skipped_ingredients'].append({
                        'naam': naam,
                        'reden': f'Fout bij toevoegen: {str(e)}'
                    })
            
            conn.commit()
            result['success'] = True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error during Excel processing: {str(e)}", exc_info=True)
            result['error'] = str(e)
            return result
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
                
    except Exception as e:
        logger.error(f"Error during Excel preparation: {str(e)}", exc_info=True)
        result['error'] = str(e)
        
    return result
