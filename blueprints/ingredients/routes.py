import csv
import io
from flask import (
    render_template, redirect, url_for, flash, request, 
    session, jsonify, current_app, send_file
)
from werkzeug.utils import secure_filename
from . import bp
from utils.db import get_db_connection
import logging
from flask_wtf import FlaskForm

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

@bp.route('/dashboard/<chef_naam>/ingredients', methods=['GET', 'POST'], endpoint='manage')
@login_required
def manage_ingredients(chef_naam):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    form = FlaskForm()  # Add this line for CSRF validation
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            # Process ingredient form submission
            naam = request.form.get('naam')
            categorie = request.form.get('categorie')
            eenheid = request.form.get('eenheid')
            prijs_per_eenheid = request.form.get('prijs_per_eenheid')
            leverancier_id = request.form.get('leverancier_id')
            
            # Validate form data
            if not naam or not categorie or not eenheid:
                flash("Naam, categorie en eenheid zijn verplicht.", "danger")
                return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
            
            # Convert empty leverancier_id to None
            if not leverancier_id:
                leverancier_id = None
            
            # Insert into database
            try:
                prijs = float(prijs_per_eenheid.replace(',', '.')) if prijs_per_eenheid else 0
                
                cur.execute("""
                    INSERT INTO ingredients (naam, categorie, eenheid, prijs_per_eenheid, leverancier_id, chef_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (naam, categorie, eenheid, prijs, leverancier_id, session['chef_id']))
                
                conn.commit()
                flash("Ingrediënt succesvol toegevoegd!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Fout bij toevoegen ingrediënt: {str(e)}", "danger")

        # Haal unieke categorieën op
        cur.execute("""
            SELECT DISTINCT categorie 
            FROM ingredients 
            WHERE chef_id = %s
        """, (session['chef_id'],))
        unieke_categorieen = [row['categorie'] for row in cur.fetchall()]

        # Haal alle ingrediënten op
        filter_categorie = request.args.get('filter_categorie')
        if filter_categorie:
            cur.execute("""
                SELECT i.*, l.naam as leverancier_naam 
                FROM ingredients i
                LEFT JOIN leveranciers l ON i.leverancier_id = l.leverancier_id
                WHERE i.chef_id = %s AND i.categorie = %s
                ORDER BY i.naam
            """, (session['chef_id'], filter_categorie))
        else:
            cur.execute("""
                SELECT i.*, l.naam as leverancier_naam 
                FROM ingredients i
                LEFT JOIN leveranciers l ON i.leverancier_id = l.leverancier_id
                WHERE i.chef_id = %s
                ORDER BY i.naam
            """, (session['chef_id'],))
            
        alle_ingredienten = cur.fetchall()

        # Haal alle leveranciers op voor de dropdown
        cur.execute("""
            SELECT * FROM leveranciers
            WHERE chef_id = %s
            ORDER BY naam
        """, (session['chef_id'],))
        leveranciers = cur.fetchall()

        # Haal alle eenheden op voor de dropdown
        cur.execute("""
            SELECT * FROM eenheden
            WHERE chef_id = %s
            ORDER BY naam
        """, (session['chef_id'],))
        eenheden = cur.fetchall()

        # Haal alle categorieën op voor de dropdown
        cur.execute("""
            SELECT * FROM categorieen
            WHERE chef_id = %s
            ORDER BY naam
        """, (session['chef_id'],))
        categorieen = cur.fetchall()

        return render_template('manage_ingredients.html',
                            chef_naam=chef_naam,
                            ingredienten=alle_ingredienten,
                            unieke_categorieen=unieke_categorieen,
                            filter_categorie=filter_categorie,
                            leveranciers=leveranciers,
                            eenheden=eenheden,
                            categorieen=categorieen,
                            form=form)

    except Exception as e:
        logger.error(f'Error in manage_ingredients: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('dashboard', chef_naam=chef_naam))
    
    finally:
        cur.close()
        conn.close()

@bp.route('/dashboard/<chef_naam>/ingredients/bulk_add', methods=['POST'])
@login_required
def bulk_add_ingredients(chef_naam):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    if 'csv_file' not in request.files:
        flash("Geen bestand geselecteerd.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    file = request.files['csv_file']

    # Check file size
    if len(file.read()) > current_app.config['MAX_CONTENT_LENGTH']:
        flash("Bestand is te groot. Maximale grootte is 5MB.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    file.seek(0)  # Reset file pointer to the beginning
    filename = secure_filename(file.filename)
    if filename == '':
        flash("Geen bestand geselecteerd.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    if not file.filename.endswith('.csv'):
        flash("Ongeldig bestandstype. Upload een CSV-bestand.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    if file.content_length > current_app.config['MAX_CONTENT_LENGTH']:
        flash("Bestand is te groot. Maximale grootte is 5MB.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    cur = conn.cursor()

    try:
        csv_reader = csv.reader(io.StringIO(file.stream.read().decode('utf-8')))
        headers = next(csv_reader)  # Get header row
        
        # Map column indices to expected fields
        column_map = {
            'naam': 0,
            'categorie': 1,
            'eenheid': 2,
            'prijs': 3
        }
        
        # Try to map columns by name if headers exist
        if headers:
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if header_lower in ['naam', 'ingredient', 'name']:
                    column_map['naam'] = i
                elif header_lower in ['categorie', 'category']:
                    column_map['categorie'] = i
                elif header_lower in ['eenheid', 'unit']:
                    column_map['eenheid'] = i
                elif header_lower in ['prijs_per_eenheid', 'prijs', 'price']:
                    column_map['prijs'] = i
        
        rows_added = 0
        for row in csv_reader:
            if len(row) >= max(column_map.values()) + 1:  # Ensure row has enough columns
                naam = row[column_map['naam']].strip()
                categorie = row[column_map['categorie']].strip() if len(row) > column_map['categorie'] else "Overig"
                eenheid = row[column_map['eenheid']].strip() if len(row) > column_map['eenheid'] else "stuk"
                
                # Safe price parsing - handle possible format issues
                prijs_per_eenheid = 0
                if len(row) > column_map['prijs']:
                    prijs_str = row[column_map['prijs']].strip()
                    try:
                        # Handle various formats: '1,23', '1.23', '€1,23'
                        prijs_str = prijs_str.replace('€', '').replace(' ', '')
                        prijs_per_eenheid = float(prijs_str.replace(',', '.')) if prijs_str else 0
                    except ValueError:
                        # If conversion fails, set price to 0 and continue
                        logger.warning(f"Could not parse price '{prijs_str}' for ingredient '{naam}' - using 0")
                
                # Insert into database
                cur.execute("""
                    INSERT INTO ingredients (naam, categorie, eenheid, prijs_per_eenheid, chef_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (naam, categorie, eenheid, prijs_per_eenheid, session['chef_id']))
                rows_added += 1
        
        conn.commit()
        flash(f"Succesvol {rows_added} ingrediënten toegevoegd!", "success")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in bulk_add_ingredients: {str(e)}")
        flash(f"Fout bij toevoegen ingrediënten: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

@bp.route('/download_csv_template')
def download_csv_template():
    """
    Serve a CSV template for bulk adding ingredients.
    """
    csv_content = io.StringIO()
    csv_writer = csv.writer(csv_content)  # Maak een csv.writer object aan
    csv_writer.writerow(['naam', 'categorie', 'eenheid', 'prijs_per_eenheid'])
    csv_writer.writerow(['Voorbeeld Naam', 'Voorbeeld Categorie', 'gram (g)', '0.00'])

    csv_content.seek(0)
    return send_file(
        io.BytesIO(csv_content.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='ingredienten_template.csv'
    )

@bp.route('/dashboard/<chef_naam>/ingredients/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_ingredients(chef_naam):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    
    form = FlaskForm()
    if not form.validate_on_submit():
        flash("Ongeldige CSRF-token. Probeer het opnieuw.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    
    filter_type = request.form.get('filter_type')
    filter_value = request.form.get('filter_value')
    
    if not filter_type or not filter_value:
        flash("Ongeldige selectie voor bulk verwijdering.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    
    cur = conn.cursor(dictionary=True)
    
    try:
        # Count ingredients to be deleted
        if filter_type == 'leverancier':
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM ingredients i
                JOIN leveranciers l ON i.leverancier_id = l.leverancier_id
                WHERE i.chef_id = %s AND l.leverancier_id = %s
            """, (session['chef_id'], filter_value))
            count = cur.fetchone()['count']
            
            if count > 0:
                cur.execute("""
                    DELETE i FROM ingredients i
                    JOIN leveranciers l ON i.leverancier_id = l.leverancier_id
                    WHERE i.chef_id = %s AND l.leverancier_id = %s
                """, (session['chef_id'], filter_value))
                conn.commit()
                flash(f"{count} ingrediënten verwijderd van geselecteerde leverancier.", "success")
            else:
                flash("Geen ingrediënten gevonden voor deze leverancier.", "warning")
        
        elif filter_type == 'categorie':
            cur.execute("""
                SELECT COUNT(*) as count FROM ingredients
                WHERE chef_id = %s AND categorie = %s
            """, (session['chef_id'], filter_value))
            count = cur.fetchone()['count']
            
            if count > 0:
                cur.execute("""
                    DELETE FROM ingredients
                    WHERE chef_id = %s AND categorie = %s
                """, (session['chef_id'], filter_value))
                conn.commit()
                flash(f"{count} ingrediënten verwijderd uit categorie '{filter_value}'.", "success")
            else:
                flash("Geen ingrediënten gevonden in deze categorie.", "warning")
        
        elif filter_type == 'alle' and filter_value == 'alle':
            cur.execute("""
                SELECT COUNT(*) as count FROM ingredients
                WHERE chef_id = %s
            """, (session['chef_id'],))
            count = cur.fetchone()['count']
            
            if count > 0:
                cur.execute("""
                    DELETE FROM ingredients
                    WHERE chef_id = %s
                """, (session['chef_id'],))
                conn.commit()
                flash(f"Alle {count} ingrediënten verwijderd.", "success")
            else:
                flash("Je hebt nog geen ingrediënten toegevoegd.", "warning")
        else:
            flash("Ongeldige selectie voor bulk verwijdering.", "danger")
    
    except Exception as e:
        conn.rollback()
        logger.error(f'Error in bulk_delete_ingredients: {str(e)}')
        flash(f"Fout bij verwijderen ingrediënten: {str(e)}", "danger")
    
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

@bp.route('/dashboard/<chef_naam>/ingredients/<int:ingredient_id>', methods=['GET', 'POST'], endpoint='edit')
@login_required
def edit_ingredient(chef_naam, ingredient_id):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    cur = conn.cursor(dictionary=True)

    # Haal info over het ingrediënt op (check of het bij deze chef hoort)
    cur.execute("""
        SELECT i.*, l.naam as leverancier_naam 
        FROM ingredients i
        LEFT JOIN leveranciers l ON i.leverancier_id = l.leverancier_id
        WHERE i.ingredient_id = %s AND i.chef_id = %s
    """, (ingredient_id, session['chef_id']))
    ingredient = cur.fetchone()
    if not ingredient:
        cur.close()
        conn.close()
        flash("Ingrediënt niet gevonden of je hebt geen toestemming.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))

    if request.method == 'POST':
        naam = request.form.get('naam')
        categorie = request.form.get('categorie')
        eenheid = request.form.get('eenheid')
        prijs_per_eenheid = request.form.get('prijs_per_eenheid')
        leverancier_id = request.form.get('leverancier_id')

        # Convert empty leverancier_id to None
        if not leverancier_id:
            leverancier_id = None

        try:
            # Convert price to float
            prijs = float(prijs_per_eenheid.replace(',', '.')) if prijs_per_eenheid else 0
            
            # Update ingredient
            cur.execute("""
                UPDATE ingredients 
                SET naam = %s, categorie = %s, eenheid = %s, prijs_per_eenheid = %s, leverancier_id = %s
                WHERE ingredient_id = %s AND chef_id = %s
            """, (naam, categorie, eenheid, prijs, leverancier_id, ingredient_id, session['chef_id']))
            
            conn.commit()
            flash("Ingrediënt succesvol bijgewerkt!", "success")
            
            # Update all dish_ingredients prices where this ingredient is used
            cur.execute("""
                UPDATE dish_ingredients di
                SET prijs_totaal = di.hoeveelheid * %s
                WHERE di.ingredient_id = %s
            """, (prijs, ingredient_id))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            flash(f"Fout bij bijwerken ingrediënt: {str(e)}", "danger")

        # Haal alle gerechten op waarin dit ingrediënt wordt gebruikt
        cur.execute("""
            SELECT d.naam, di.hoeveelheid, di.prijs_totaal
            FROM dishes d
            JOIN dish_ingredients di ON d.dish_id = di.dish_id
            WHERE di.ingredient_id = %s
        """, (ingredient_id,))
        gerechten_met_ingredient = cur.fetchall()

        cur.close()
        conn.close()
        return redirect(url_for('ingredients.edit', chef_naam=chef_naam, ingredient_id=ingredient_id))

    # Haal alle leveranciers op voor de dropdown
    cur.execute("""
        SELECT * FROM leveranciers
        WHERE chef_id = %s
        ORDER BY naam
    """, (session['chef_id'],))
    leveranciers = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('edit_ingredient.html', chef_naam=chef_naam, ingredient=ingredient, leveranciers=leveranciers, form=FlaskForm())

@bp.route('/dashboard/<chef_naam>/ingredients/<int:ingredient_id>/update-field', methods=['POST'])
@login_required
def update_ingredient_field(chef_naam, ingredient_id):
    """Update een ingrediëntveld en herbereken kostprijzen indien nodig"""
    if session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'message': 'Unauthorized'})

    try:
        data = request.get_json()
        field = data['field']
        value = data['value']

        # Validate ingredient name
        if field == 'naam' and not value.strip():
            return jsonify({'success': False, 'message': 'Naam mag niet leeg zijn'})

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Database connection error'})

        cur = conn.cursor(dictionary=True)
        try:
            # Special handling for price field
            if field == 'prijs_per_eenheid':
                try:
                    # Convert price string to float
                    price = float(value.replace(',', '.'))
                    
                    # Update ingredient price
                    cur.execute("""
                        UPDATE ingredients 
                        SET prijs_per_eenheid = %s
                        WHERE ingredient_id = %s AND chef_id = %s
                    """, (price, ingredient_id, session['chef_id']))
                    
                    # Update all dish_ingredients prices where this ingredient is used
                    cur.execute("""
                        UPDATE dish_ingredients di
                        SET prijs_totaal = di.hoeveelheid * %s
                        WHERE di.ingredient_id = %s
                    """, (price, ingredient_id))
                    
                    conn.commit()
                    return jsonify({'success': True})
                    
                except ValueError:
                    return jsonify({'success': False, 'message': 'Ongeldige prijs'})
            else:
                # For other fields, do simple update
                cur.execute(f"""
                    UPDATE ingredients 
                    SET {field} = %s
                    WHERE ingredient_id = %s AND chef_id = %s
                """, (value, ingredient_id, session['chef_id']))
                
                conn.commit()
                return jsonify({'success': True})
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating ingredient field: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/dashboard/<chef_naam>/ingredients/<int:ingredient_id>/delete', methods=['POST'])
@login_required
def delete_ingredient(chef_naam, ingredient_id):
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM ingredients WHERE ingredient_id = %s AND chef_id = %s", (ingredient_id, session['chef_id']))
        conn.commit()
        flash("Ingrediënt succesvol verwijderd!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Fout bij verwijderen ingrediënt: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('ingredients.manage', chef_naam=chef_naam))
