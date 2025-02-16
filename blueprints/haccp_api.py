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
