import os
import csv
import io
from flask import render_template, redirect, url_for, flash, request, session, current_app, send_file, jsonify, Markup
from werkzeug.utils import secure_filename
from . import bp
from utils.db import get_db_connection
import logging
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from mysql.connector import Error  # Add this import for Error

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

@bp.route('/template', methods=['GET'])
@login_required
def download_template():
    """Download a CSV template for ingredients"""
    # First check if there's a template in S3
    if current_app.config.get('USE_S3'):
        try:
            s3_client = boto3.client(
                's3',
                region_name='eu-west-1',
                aws_access_key_id=current_app.config.get('S3_KEY'),
                aws_secret_access_key=current_app.config.get('S3_SECRET')
            )
            
            template_key = "templates/ingredients_template.csv"
            
            try:
                # Check if template exists in S3
                response = s3_client.get_object(
                    Bucket=current_app.config.get('S3_BUCKET'),
                    Key=template_key
                )
                
                # If exists, return the S3 template
                content = response['Body'].read()
                mem = io.BytesIO(content)
                mem.seek(0)
                
                logger.info(f"Using ingredients template from S3: {template_key}")
                return send_file(
                    mem,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name='ingredienten_template.csv'
                )
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.info("No template found in S3, using generated template")
                else:
                    logger.error(f"Error retrieving S3 template: {str(e)}")
                # Fall through to generated template
                
        except Exception as e:
            logger.error(f"Error connecting to S3 for template: {str(e)}")
            # Fall through to generated template
    
    # If S3 is not configured or template not found, generate one
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header and example rows (updated with better examples)
    writer.writerow(['ingredient', 'categorie', 'eenheid', 'prijs_per_eenheid', 'leverancier'])
    writer.writerow(['Aardappelen', 'Groenten', 'kg', '1.25', 'Lokale Boerderij'])
    writer.writerow(['Kipfilet', 'Vlees', 'kg', '8.50', 'Slagerij Jansen'])
    writer.writerow(['Olijfolie', 'Voorraad', 'liter', '12.75', 'De Olijf'])
    writer.writerow(['Knoflook', 'Groenten', 'stuk', '0.30', ''])
    writer.writerow(['Melk', 'Zuivel', 'liter', '1.15', ''])
    
    # Create a bytes buffer from the string buffer
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))  # Include BOM for Excel compatibility
    mem.seek(0)
    
    logger.info("Using generated ingredients template")
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name='ingredienten_template.csv'
    )

@bp.route('/from-file', methods=['POST'])
@login_required
def import_from_file():
    """Import ingredients from uploaded CSV file"""
    chef_id = session.get('chef_id')
    chef_naam = session.get('chef_naam')
    
    if 'csv_file' not in request.files:
        flash("Geen bestand geüpload", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash("Geen bestand geselecteerd", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
    
    # Process the uploaded CSV file
    try:
        # Read the file content
        stream = io.StringIO(file.stream.read().decode('utf-8-sig', errors='ignore'))
        
        # Check if update_existing checkbox is checked
        update_existing = 'update_existing' in request.form
        
        result = process_csv(stream, chef_id, update_existing=update_existing)
        
        # Return response based on result
        if result['success']:
            flash(f"Succesvol {result['imported']} ingrediënten geïmporteerd. "
                  f"{result['updated'] if 'updated' in result else 0} ingrediënten bijgewerkt. "
                  f"{result['skipped']} ingrediënten overgeslagen.", "success")
        else:
            flash(f"Er was een probleem bij het importeren: {result['error']}", "danger")
            
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))
        
    except Exception as e:
        logger.error(f"CSV import error: {str(e)}", exc_info=True)
        flash(f"Fout bij het verwerken van het CSV bestand: {str(e)}", "danger")
        return redirect(url_for('manage_ingredients', chef_naam=chef_naam))

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
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
    
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
            return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
        
        # Get the CSV file path
        csv_path = supplier.get('csv_file_path')
        
        if not csv_path:
            flash("Geen CSV-bestand geconfigureerd voor deze leverancier", "danger")
            return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
        
        logger.info(f"Processing CSV from path: {csv_path}")
        stream = None
        
        try:
            # Check if using S3 storage
            if current_app.config.get('USE_S3'):
                # Get file from S3
                s3_client = boto3.client(
                    's3',
                    region_name='eu-west-1',
                    aws_access_key_id=current_app.config.get('S3_KEY'),
                    aws_secret_access_key=current_app.config.get('S3_SECRET')
                )
                
                try:
                    # Get the CSV file content
                    logger.debug(f"Retrieving file from S3: {csv_path}")
                    response = s3_client.get_object(
                        Bucket=current_app.config.get('S3_BUCKET'),
                        Key=csv_path
                    )
                    
                    # Read and decode the CSV content
                    csv_content = response['Body'].read().decode('utf-8')
                    stream = io.StringIO(csv_content)
                    logger.debug(f"Successfully retrieved CSV content from S3")
                    
                except ClientError as e:
                    logger.error(f"Error retrieving CSV from S3: {str(e)}")
                    flash(f"Fout bij ophalen bestand: {str(e)}", "danger")
                    return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
            else:
                # Get file from local storage
                local_path = os.path.join(current_app.root_path, 'static', csv_path)
                if os.path.exists(local_path):
                    with open(local_path, 'r', encoding='utf-8') as f:
                        csv_content = f.read()
                    stream = io.StringIO(csv_content)
                    logger.debug(f"Successfully read CSV from local file system")
                else:
                    logger.error(f"Local CSV file not found: {local_path}")
                    flash("CSV bestand niet gevonden op de server", "danger")
                    return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
            
            if stream:
                # Process the CSV in chunks to avoid timeout
                result = process_csv_in_chunks(stream, chef_id, default_supplier=supplier, update_existing=update_existing)
                
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
                flash("Kon CSV-bestand niet verwerken", "danger")
                
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}", exc_info=True)
            flash(f"Fout bij verwerken bestand: {str(e)}", "danger")
        
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Import ingredients error: {str(e)}", exc_info=True)
        flash(f"Er is een fout opgetreden bij het importeren: {str(e)}", "danger")
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def process_csv_in_chunks(stream, chef_id, default_supplier=None, update_existing=False, chunk_size=50):
    """
    Process a CSV file in chunks to avoid timeout issues
    
    Args:
        stream: StringIO object containing CSV data
        chef_id: ID of the chef
        default_supplier: Supplier info to use as default
        update_existing: Whether to update existing ingredients
        chunk_size: Number of records to process in each batch
        
    Returns:
        dict with results
    """
    logger.info(f"Starting CSV processing in chunks of {chunk_size}")
    result = {
        'success': False,
        'imported': 0,
        'skipped': 0,
        'skipped_ingredients': [],  # Add this to track skipped ingredients
        'error': None
    }
    
    try:
        reader = csv.reader(stream)
        # Skip the header row
        headers = next(reader, None)
        if not headers:
            result['error'] = "CSV-bestand is leeg of heeft geen headers"
            return result
            
        # Validate headers
        expected_columns = ['naam', 'categorie', 'eenheid', 'prijs']
        if len(headers) < len(expected_columns):
            result['error'] = f"CSV-bestand heeft niet alle vereiste kolommen. Verwacht: {', '.join(expected_columns)}"
            return result
        
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
                
            # Process in chunks
            rows = []
            for row in reader:
                rows.append(row)
                
                # Process when we reach chunk_size or end of file
                if len(rows) >= chunk_size:
                    process_result = process_chunk(rows, chef_id, cur, conn, existing_ingredients, 
                                                 categories, units, default_supplier, update_existing)
                    
                    result['imported'] += process_result['imported']
                    result['skipped'] += process_result['skipped']
                    result['skipped_ingredients'].extend(process_result['skipped_ingredients'])
                    rows = []  # Reset for next chunk
            
            # Process any remaining rows
            if rows:
                process_result = process_chunk(rows, chef_id, cur, conn, existing_ingredients, 
                                             categories, units, default_supplier, update_existing)
                
                result['imported'] += process_result['imported']
                result['skipped'] += process_result['skipped']
                result['skipped_ingredients'].extend(process_result['skipped_ingredients'])
                
            result['success'] = True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error during CSV processing: {str(e)}", exc_info=True)
            result['error'] = str(e)
            return result
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
                
    except Exception as e:
        logger.error(f"Error during CSV preparation: {str(e)}", exc_info=True)
        result['error'] = str(e)
        
    return result

def process_chunk(rows, chef_id, cur, conn, existing_ingredients, categories, units, default_supplier, update_existing):
    """Process a chunk of CSV rows"""
    result = {'imported': 0, 'skipped': 0, 'skipped_ingredients': []}
    
    for row in rows:
        if len(row) < 4:  # Ensure we have all required fields
            result['skipped'] += 1
            if len(row) > 0 and row[0]:
                result['skipped_ingredients'].append({
                    'naam': row[0].strip(),
                    'reden': 'Onvolledige gegevens'
                })
            continue
            
        naam = row[0].strip()
        categorie = row[1].strip() if len(row) > 1 and row[1] else "Overig"
        eenheid = row[2].strip() if len(row) > 2 and row[2] else "stuk"
        
        try:
            prijs = float(row[3].replace(',', '.')) if len(row) > 3 and row[3] else 0.0
        except ValueError:
            prijs = 0.0
            
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
                    """, (prijs, default_supplier['leverancier_id'], ingredient_id))
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
        
        # Insert the ingredient with category name (assuming the table uses category name not ID)
        try:
            cur.execute("""
                INSERT INTO ingredients 
                (naam, categorie, eenheid, prijs_per_eenheid, leverancier_id, chef_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (naam, categorie, eenheid, prijs, default_supplier['leverancier_id'], chef_id))
            result['imported'] += 1
        except Exception as e:
            logger.warning(f"Failed to insert ingredient {naam}: {str(e)}")
            result['skipped'] += 1
            result['skipped_ingredients'].append({
                'naam': naam,
                'reden': f'Fout bij toevoegen: {str(e)}'
            })
    
    conn.commit()
    return result

def get_supplier_csv_content(csv_path):
    """Get the content of a supplier's CSV file"""
    if current_app.config.get('USE_S3'):
        # For S3 storage
        try:
            s3_client = boto3.client(
                's3',
                region_name='eu-west-1',
                aws_access_key_id=current_app.config.get('S3_KEY'),
                aws_secret_access_key=current_app.config.get('S3_SECRET')
            )
            
            # Get the CSV file content
            response = s3_client.get_object(
                Bucket=current_app.config.get('S3_BUCKET'),
                Key=csv_path
            )
            
            # Read and decode the CSV content
            return response['Body'].read().decode('utf-8-sig', errors='ignore')
                
        except Exception as e:
            logger.error(f"Error reading CSV from S3: {str(e)}")
            return None
    else:
        # For local storage
        local_csv_path = os.path.join(current_app.root_path, 'static', csv_path)
        
        if not os.path.exists(local_csv_path):
            logger.error(f"CSV file not found: {local_csv_path}")
            return None
        
        try:
            with open(local_csv_path, 'r', encoding='utf-8-sig') as file:
                return file.read()
                
        except Exception as e:
            logger.error(f"Error reading local CSV: {str(e)}")
            return None

def process_csv(csv_stream, chef_id, default_supplier=None, update_existing=False):
    """Process CSV content and import ingredients
    
    Args:
        csv_stream: StringIO object containing CSV content
        chef_id: ID of the chef importing the ingredients
        default_supplier: Optional supplier object to use if not specified in CSV
        update_existing: Whether to update existing ingredients instead of skipping them
        
    Returns:
        dict with results: {success, imported, updated, skipped, error}
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed", "imported": 0, "updated": 0, "skipped": 0}
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # First, check the actual database structure to see which columns exist
        logger.info("Checking database table structure...")
        available_columns = []
        try:
            cur.execute("SHOW COLUMNS FROM ingredients")  # Using SHOW COLUMNS instead of DESCRIBE for better compatibility
            available_columns = [row['Field'].lower() for row in cur.fetchall()]
            logger.info(f"Available columns in ingredients table: {available_columns}")
        except Exception as e:
            logger.error(f"Error checking table structure: {str(e)}")
            # Continue with default structure assuming minimal fields only
            available_columns = ['naam', 'prijs_per_eenheid', 'leverancier_id', 'chef_id']
        
        # Check for specific columns - note we're using lowercase for comparison
        has_eenheid_id = 'eenheid_id' in available_columns
        has_eenheid = 'eenheid' in available_columns
        has_categorie_id = 'categorie_id' in available_columns
        logger.info(f"Column check: eenheid_id exists: {has_eenheid_id}, eenheid exists: {has_eenheid}, categorie_id exists: {has_categorie_id}")
        
        # Get existing ingredients to avoid duplicates or update if needed
        if update_existing:
            # Build a dynamic query based on available columns
            select_columns = ['ingredient_id', 'LOWER(naam) as lower_naam', 'naam', 'prijs_per_eenheid', 'leverancier_id']
            
            if has_eenheid_id:
                select_columns.append('eenheid_id')
            
            if has_categorie_id:
                select_columns.append('categorie_id')
            
            # Execute dynamic query to get existing ingredients
            query = f"SELECT {', '.join(select_columns)} FROM ingredients WHERE chef_id = %s"
            logger.info(f"Dynamic SELECT query: {query}")
            
            cur.execute(query, (chef_id,))
            existing_ingredients_data = {row['lower_naam']: row for row in cur.fetchall()}
            existing_ingredients = set(existing_ingredients_data.keys())
        else:
            # If not updating, just get names for skipping
            cur.execute("SELECT LOWER(naam) as naam FROM ingredients WHERE chef_id = %s", (chef_id,))
            existing_ingredients = {row['naam'] for row in cur.fetchall()}
        
        # Track import statistics
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Parse CSV
        csv_reader = csv.DictReader(csv_stream)
        required_fields = ["ingredient"]
        
        # Check if we have the required fields
        for field in required_fields:
            if field not in csv_reader.fieldnames and field.lower() not in csv_reader.fieldnames:
                alternative_fields = {"ingredient": ["naam", "name"]}
                found_alternative = False
                
                if field in alternative_fields:
                    for alt in alternative_fields[field]:
                        if alt in csv_reader.fieldnames or alt.lower() in csv_reader.fieldnames:
                            found_alternative = True
                            break
                            
                if not found_alternative:
                    return {
                        "success": False, 
                        "error": f"Verplicht veld '{field}' ontbreekt in CSV", 
                        "imported": 0, 
                        "updated": 0, 
                        "skipped": 0
                    }
        
        # Process rows
        for row in csv_reader:
            # Skip empty rows
            if not any(row.values()):
                continue
            
            # Extract and normalize field names
            naam = None
            for field in ["ingredient", "naam", "name"]:
                if field in row and row[field]:
                    naam = row[field].strip()
                    break
                if field.lower() in row and row[field.lower()]:
                    naam = row[field.lower()].strip()
                    break
            
            # Skip if no name is provided
            if not naam:
                skipped_count += 1
                continue
            
            # Handle existing ingredients
            if naam.lower() in existing_ingredients:
                if update_existing:
                    # Update existing ingredient
                    existing_ingredient = existing_ingredients_data[naam.lower()]
                    
                    # Extract remaining fields with fallbacks
                    categorie = get_field_value(row, ["categorie", "category"], "Overig")
                    eenheid = get_field_value(row, ["eenheid", "unit"], "stuk")
                    leverancier_naam = get_field_value(row, ["leverancier", "supplier"], None)
                    
                    # Parse price
                    prijs = None
                    prijs_str = get_field_value(row, ["prijs_per_eenheid", "price", "prijs"], None)
                    if prijs_str:
                        try:
                            prijs = float(prijs_str.replace(',', '.'))
                        except:
                            pass
                    
                    # Handle supplier logic
                    leverancier_id = None
                    if leverancier_naam:
                        # Check if supplier exists
                        cur.execute("""
                            SELECT leverancier_id FROM leveranciers 
                            WHERE LOWER(naam) = LOWER(%s) AND (chef_id = %s OR is_admin_created = TRUE)
                        """, (leverancier_naam, chef_id))
                        supplier_row = cur.fetchone()
                        
                        if supplier_row:
                            leverancier_id = supplier_row['leverancier_id']
                        else:
                            # Create new supplier if it doesn't exist
                            cur.execute("""
                                INSERT INTO leveranciers (naam, chef_id) 
                                VALUES (%s, %s)
                            """, (leverancier_naam, chef_id))
                            leverancier_id = cur.lastrowid
                    elif default_supplier:
                        leverancier_id = default_supplier['leverancier_id']
                    else:
                        # Keep existing supplier if not specified
                        leverancier_id = existing_ingredient['leverancier_id']
                    
                    # Build update query dynamically based on what's provided
                    update_fields = []
                    update_values = []
                    
                    if prijs is not None:
                        update_fields.append("prijs_per_eenheid = %s")
                        update_values.append(prijs)
                    
                    if leverancier_id is not None:
                        update_fields.append("leverancier_id = %s")
                        update_values.append(leverancier_id)
                    
                    # Only update if we have something to update
                    if update_fields:
                        update_query = f"""
                            UPDATE ingredients 
                            SET {', '.join(update_fields)}
                            WHERE ingredient_id = %s
                        """
                        update_values.append(existing_ingredient['ingredient_id'])
                        
                        logger.info(f"Updating ingredient: {naam}")
                        cur.execute(update_query, update_values)
                        updated_count += 1
                        logger.info(f"Successfully updated: {naam}")
                    else:
                        # Nothing to update
                        skipped_count += 1
                else:
                    # Skip if ingredient exists and we're not updating
                    skipped_count += 1
                    continue
            else:
                # Add new ingredient 
                # Extract remaining fields with fallbacks
                categorie = get_field_value(row, ["categorie", "category"], "Overig")
                eenheid = get_field_value(row, ["eenheid", "unit"], "stuk")
                leverancier_naam = get_field_value(row, ["leverancier", "supplier"], None)
                
                # Parse price
                prijs = 0.0
                prijs_str = get_field_value(row, ["prijs_per_eenheid", "price", "prijs"], "0")
                try:
                    prijs = float(prijs_str.replace(',', '.'))
                except:
                    pass
                    
                # Handle supplier logic
                leverancier_id = None
                
                # If supplier name is provided in CSV
                if leverancier_naam:
                    # Check if supplier exists
                    cur.execute("""
                        SELECT leverancier_id FROM leveranciers 
                        WHERE LOWER(naam) = LOWER(%s) AND (chef_id = %s OR is_admin_created = TRUE)
                    """, (leverancier_naam, chef_id))
                    supplier_row = cur.fetchone()
                    
                    if supplier_row:
                        leverancier_id = supplier_row['leverancier_id']
                    else:
                        # Create new supplier if it doesn't exist
                        cur.execute("""
                            INSERT INTO leveranciers (naam, chef_id) 
                            VALUES (%s, %s)
                        """, (leverancier_naam, chef_id))
                        leverancier_id = cur.lastrowid
                
                # Use default supplier if provided and no supplier in CSV
                elif default_supplier:
                    leverancier_id = default_supplier['leverancier_id']
                
                # Always handle category - create it if it doesn't exist
                categorie_id = None
                if has_categorie_id:
                    # Get or create category ID
                    categorie_id = get_or_create_category(cur, chef_id, categorie)
                
                # Get or create unit (only if the column exists)
                eenheid_id = None
                if has_eenheid_id:
                    eenheid_id = get_or_create_unit(cur, chef_id, eenheid)
                
                # Dynamically build SQL based on available columns
                columns = ['naam', 'prijs_per_eenheid', 'chef_id']
                values = [naam, prijs, chef_id]
                
                # Only include leverancier_id if we have it
                if leverancier_id is not None:
                    columns.append('leverancier_id')
                    values.append(leverancier_id)
                
                # Always include the categorie field
                columns.append('categorie')
                values.append(categorie)
                
                # Only include the eenheid field if it exists in the schema
                if has_eenheid:
                    columns.append('eenheid')
                    values.append(eenheid if eenheid else 'gr')  # Default to 'gr' if empty
                
                # Only include the categorie_id if it exists in the schema and we have a value
                if has_categorie_id and categorie_id is not None:
                    columns.append('categorie_id')
                    values.append(categorie_id)
                
                # Only include the eenheid_id if it exists in the schema and we have a value
                if has_eenheid_id and eenheid_id is not None:
                    columns.append('eenheid_id')
                    values.append(eenheid_id)
                
                # Build the SQL query dynamically with error handling
                try:
                    columns_str = ', '.join(columns)
                    placeholders = ', '.join(['%s'] * len(values))
                    
                    logger.info(f"Inserting ingredient: {naam} with columns: {columns_str}")
                    insert_query = f"""
                        INSERT INTO ingredients (
                            {columns_str}
                        ) VALUES ({placeholders})
                    """
                    logger.debug(f"SQL: {insert_query}, Values: {values}")
                    cur.execute(insert_query, values)
                    imported_count += 1
                    logger.info(f"Successfully imported: {naam}")
                except Error as sql_error:
                    # Special handling for MySQL errors
                    logger.error(f"SQL error: {str(sql_error)}")
                    
                    # If it's an unknown column error, try a minimal insert with just the name, price and category
                    if "Unknown column" in str(sql_error):
                        try:
                            logger.info("Retrying with minimal fields plus category")
                            cur.execute("""
                                INSERT INTO ingredients (naam, prijs_per_eenheid, categorie, chef_id)
                                VALUES (%s, %s, %s, %s)
                            """, (naam, prijs, categorie, chef_id))
                            imported_count += 1
                            logger.info(f"Successfully imported with minimal fields: {naam}")
                        except Exception as minimal_error:
                            logger.error(f"Failed even with minimal fields: {str(minimal_error)}")
                            skipped_count += 1
                    else:
                        # Not a column error, skip this ingredient
                        logger.error(f"Skipping ingredient due to SQL error: {naam}")
                        skipped_count += 1
                except Exception as e:
                    logger.error(f"Error inserting ingredient '{naam}': {str(e)}")
                    skipped_count += 1

        conn.commit()
        
        return {
            "success": True, 
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count, 
            "error": None
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"CSV processing error: {str(e)}", exc_info=True)
        return {
            "success": False, 
            "error": str(e), 
            "imported": 0, 
            "updated": 0, 
            "skipped": 0
        }
    finally:
        cur.close()
        conn.close()

def get_field_value(row, field_options, default=None):
    """Extract field value from row with multiple possible field names"""
    for field in field_options:
        if field in row and row[field]:
            return row[field].strip()
        # Check lowercase version too
        if field.lower() in row and row[field.lower()]:
            return row[field.lower()].strip()
    return default

def get_or_create_category(cursor, chef_id, category_name):
    """Get existing category ID or create a new one"""
    if not category_name:
        category_name = "Overig"  # Default category if none provided
        
    # Check if category exists
    cursor.execute("""
        SELECT categorie_id FROM categorieen 
        WHERE chef_id = %s AND LOWER(naam) = LOWER(%s)
    """, (chef_id, category_name))
    category = cursor.fetchone()
    
    if category:
        return category['categorie_id']
    
    # Create new category
    try:
        cursor.execute("""
            INSERT INTO categorieen (naam, chef_id) 
            VALUES (%s, %s)
        """, (category_name, chef_id))
        logger.info(f"Created new category: {category_name}")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating category '{category_name}': {str(e)}")
        # Return None on error, allowing the code to continue without a categorie_id
        return None

def get_or_create_unit(cursor, chef_id, unit_name):
    """Get existing unit ID or create a new one"""
    # Check if unit exists
    cursor.execute("""
        SELECT eenheid_id FROM eenheden 
        WHERE chef_id = %s AND LOWER(naam) = LOWER(%s)
    """, (chef_id, unit_name))
    unit = cursor.fetchone()
    
    if unit:
        return unit['eenheid_id']
    
    # Create new unit
    cursor.execute("""
        INSERT INTO eenheden (naam, chef_id) 
        VALUES (%s, %s)
    """, (unit_name, chef_id))
    return cursor.lastrowid
