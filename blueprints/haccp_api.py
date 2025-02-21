from flask import Blueprint, request, jsonify
from utils.db import get_db_connection
from flask import session
import logging
from datetime import datetime, timedelta
import mysql.connector

bp = Blueprint('haccp_api', __name__, url_prefix='/api/haccp')

logger = logging.getLogger(__name__)

# Blueprint-level error handlers
@bp.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled exception: {e}")
    return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/checklist/<int:checklist_id>/delete', methods=['POST'])
def delete_haccp_checklist(checklist_id):
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500
        cur = conn.cursor()

        # Controleer eerst of de checklist van deze chef is
        cur.execute("""
            SELECT chef_id FROM haccp_checklists 
            WHERE checklist_id = %s
        """, (checklist_id,))
        
        result = cur.fetchone()
        if not result or result[0] != session['chef_id']:
            return jsonify({'success': False, 'error': 'Checklist niet gevonden of geen toegang'}), 404

        # Verwijder eerst alle metingen van deze checklist
        cur.execute("""
            DELETE m FROM haccp_metingen m
            JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
            WHERE c.checklist_id = %s
        """, (checklist_id,))

        # Verwijder dan alle checkpunten
        cur.execute("""
            DELETE FROM haccp_checkpunten 
            WHERE checklist_id = %s
        """, (checklist_id,))

        # Verwijder tenslotte de checklist zelf
        cur.execute("""
            DELETE FROM haccp_checklists 
            WHERE checklist_id = %s AND chef_id = %s
        """, (checklist_id, session['chef_id']))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f'Error deleting HACCP checklist: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/meting/<int:meting_id>/update', methods=['POST'])
def update_haccp_meting(meting_id):
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        # Debug logging
        logger.info(f"Received update request for meting {meting_id}")
        logger.info(f"Form data: {request.form}")

        waarde = request.form.get('waarde')
        actie_ondernomen = request.form.get('actie_ondernomen')

        if waarde is None:
            return jsonify({'success': False, 'error': 'Waarde ontbreekt'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

        cursor = conn.cursor(dictionary=True)

        try:
            # Controleer eerst of de meting bestaat en van deze chef is
            cursor.execute("""
                SELECT m.meting_id, c.grenswaarde 
                FROM haccp_metingen m
                JOIN haccp_checkpunten c ON m.punt_id = c.punt_id
                WHERE m.meting_id = %s AND m.chef_id = %s
            """, (meting_id, session['chef_id']))
            meting = cursor.fetchone()
            if not meting:
                return jsonify({'success': False, 'error': 'Meting niet gevonden'}), 404

            try:
                waarde_float = float(waarde)
            except ValueError:
                return jsonify({'success': False, 'error': 'Ongeldige waarde'}), 400

            # Update de meting (zonder explicit updated_at)
            cursor.execute("""
                UPDATE haccp_metingen 
                SET waarde = %s, actie_ondernomen = %s
                WHERE meting_id = %s 
                AND chef_id = %s
            """, (waarde_float, actie_ondernomen, meting_id, session['chef_id']))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({'success': False, 'error': 'Geen wijzigingen aangebracht'}), 400

            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Meting succesvol bijgewerkt'
            })

        except mysql.connector.Error as e:
            conn.rollback()
            logger.error(f'Database error: {str(e)}')
            return jsonify({'success': False, 'error': f'Database fout: {str(e)}'}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error updating HACCP measurement: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/hygiene/add', methods=['POST'])
def add_hygiene_control():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        data = request.form
        medewerker = data.get('medewerker')
        werkkleding_ok = data.get('werkkleding_ok') == 'true'
        handen_ok = data.get('handen_ok') == 'true'
        sieraden_ok = data.get('sieraden_ok') == 'true'
        ziekmelding_ok = data.get('ziekmelding_ok') == 'true'
        opmerking = data.get('opmerking', '')

        if not medewerker:
            return jsonify({'success': False, 'error': 'Medewerker naam is verplicht'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO haccp_hygiene_controle 
                (chef_id, medewerker, werkkleding_ok, handen_ok, sieraden_ok, 
                ziekmelding_ok, datum_tijd, opmerking)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (session['chef_id'], medewerker, werkkleding_ok, handen_ok, 
                  sieraden_ok, ziekmelding_ok, opmerking))
            
            conn.commit()
            return jsonify({
                'success': True,
                'controle_id': cursor.lastrowid
            })

        except mysql.connector.Error as e:
            conn.rollback()
            logger.error(f'Database error: {str(e)}')
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error adding hygiene control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/hygiene/list', methods=['GET'])
def list_hygiene_controls():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM haccp_hygiene_controle 
            WHERE chef_id = %s 
            ORDER BY datum_tijd DESC
        """, (session['chef_id'],))
        
        controls = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'controls': controls
        })

    except Exception as e:
        logger.error(f'Error listing hygiene controls: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/hygiene/<int:controle_id>/delete', methods=['POST'])
def delete_hygiene_control(controle_id):
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database verbinding mislukt'}), 500

        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM haccp_hygiene_controle 
                WHERE controle_id = %s AND chef_id = %s
            """, (controle_id, session['chef_id']))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Controle niet gevonden'}), 404

            conn.commit()
            return jsonify({'success': True})

        except mysql.connector.Error as e:
            conn.rollback()
            logger.error(f'Database error: {str(e)}')
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error deleting hygiene control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/ongedierte/add', methods=['POST'])
def add_pest_control():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        data = request.form
        locatie = data.get('locatie')
        type_plaag = data.get('type_plaag')
        ernst = data.get('ernst')
        actie_ondernomen = data.get('actie_ondernomen', '')
        opgelost = data.get('opgelost') == 'true'

        if not all([locatie, type_plaag, ernst]):
            return jsonify({'success': False, 'error': 'Niet alle verplichte velden zijn ingevuld'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO haccp_ongedierte 
                (chef_id, locatie, type_plaag, ernst, datum_tijd, actie_ondernomen, opgelost)
                VALUES (%s, %s, %s, %s, NOW(), %s, %s)
            """, (session['chef_id'], locatie, type_plaag, ernst, actie_ondernomen, opgelost))
            
            conn.commit()
            return jsonify({
                'success': True,
                'melding_id': cursor.lastrowid
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error adding pest control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/ongedierte/list', methods=['GET'])
def list_pest_controls():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM haccp_ongedierte 
            WHERE chef_id = %s 
            ORDER BY datum_tijd DESC
        """, (session['chef_id'],))
        
        controls = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'controls': controls
        })

    except Exception as e:
        logger.error(f'Error listing pest controls: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/ongedierte/<int:melding_id>/update', methods=['POST'])
def update_pest_control(melding_id):
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        data = request.form
        actie_ondernomen = data.get('actie_ondernomen')
        opgelost = data.get('opgelost') == 'true'

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE haccp_ongedierte 
                SET actie_ondernomen = %s, opgelost = %s
                WHERE melding_id = %s AND chef_id = %s
            """, (actie_ondernomen, opgelost, melding_id, session['chef_id']))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Melding niet gevonden'}), 404

            conn.commit()
            return jsonify({'success': True})

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error updating pest control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/productie/add', methods=['POST'])
def add_production_control():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        data = request.form
        product = data.get('product')
        batch_code = data.get('batch_code')
        kerntemperatuur = data.get('kerntemperatuur')
        producttemp_ok = data.get('producttemp_ok') == 'true'
        tijd_temp_ok = data.get('tijd_temp_ok') == 'true'
        opmerking = data.get('opmerking', '')

        if not all([product, batch_code, kerntemperatuur]):
            return jsonify({'success': False, 'error': 'Niet alle verplichte velden zijn ingevuld'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO haccp_productie 
                (chef_id, product, batch_code, kerntemperatuur, producttemp_ok, 
                tijd_temp_ok, datum_tijd, opmerking)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (session['chef_id'], product, batch_code, kerntemperatuur,
                  producttemp_ok, tijd_temp_ok, opmerking))
            
            conn.commit()
            return jsonify({
                'success': True,
                'productie_id': cursor.lastrowid
            })
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error adding production control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/productie/list', methods=['GET'])
def list_production_controls():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM haccp_productie 
            WHERE chef_id = %s 
            ORDER BY datum_tijd DESC
        """, (session['chef_id'],))
        
        controls = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'controls': controls
        })

    except Exception as e:
        logger.error(f'Error listing production controls: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/allergenen/add', methods=['POST'])
def add_allergen_control():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        data = request.form
        product_id = data.get('product_id')
        allergeen_id = data.get('allergeen_id')
        aanwezig = data.get('aanwezig') == 'true'
        kruisbesmetting = data.get('kruisbesmetting') == 'true'

        if not all([product_id, allergeen_id]):
            return jsonify({'success': False, 'error': 'Niet alle verplichte velden zijn ingevuld'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO haccp_allergenen_controle 
                (chef_id, product_id, allergeen_id, aanwezig, kruisbesmetting, datum_controle)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (session['chef_id'], product_id, allergeen_id, aanwezig, kruisbesmetting))
            
            conn.commit()
            return jsonify({
                'success': True,
                'controle_id': cursor.lastrowid
            })
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f'Error adding allergen control: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/allergenen/list', methods=['GET'])
def list_allergen_controls():
    if 'chef_id' not in session:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ac.*, p.naam as product_naam, a.naam as allergeen_naam 
            FROM haccp_allergenen_controle ac
            JOIN products p ON ac.product_id = p.product_id
            JOIN allergenen a ON ac.allergeen_id = a.allergeen_id
            WHERE ac.chef_id = %s 
            ORDER BY ac.datum_controle DESC
        """, (session['chef_id'],))
        
        controls = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'controls': controls
        })

    except Exception as e:
        logger.error(f'Error listing allergen controls: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
