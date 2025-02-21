from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from functools import wraps
from utils.db import get_db_connection
import logging
from datetime import datetime

bp = Blueprint('haccp', __name__, url_prefix='/haccp')
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'chef_id' not in session:
            flash("Geen toegang. Log opnieuw in.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/<chef_naam>')
@login_required
def dashboard(chef_naam):
    """HACCP Dashboard pagina"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('main.dashboard', chef_naam=chef_naam))

    cur = conn.cursor(dictionary=True)

    try:
        # Get all counts for today
        cur.execute("""
            SELECT COUNT(*) as count FROM haccp_ontvangst 
            WHERE chef_id = %s AND DATE(datum_tijd) = CURDATE()
        """, (session['chef_id'],))
        ontvangst_count = cur.fetchone()['count']

        cur.execute("""
            SELECT COUNT(*) as count FROM haccp_temperatuur 
            WHERE chef_id = %s AND DATE(datum_tijd) = CURDATE()
        """, (session['chef_id'],))
        temp_count = cur.fetchone()['count']

        # Get cleaning schedules due today
        cur.execute("""
            SELECT * FROM haccp_schoonmaak_planning
            WHERE chef_id = %s AND (
                frequentie = 'dagelijks'
                OR (frequentie = 'wekelijks' AND WEEKDAY(CURDATE()) = 0)
                OR (frequentie = 'maandelijks' AND DAY(CURDATE()) = 1)
            )
            ORDER BY locatie
        """, (session['chef_id'],))
        schoonmaak_taken = cur.fetchall()

        return render_template('haccp/dashboard.html',
                            chef_naam=chef_naam,
                            ontvangst_count=ontvangst_count,
                            temp_count=temp_count,
                            schoonmaak_taken=schoonmaak_taken)

    except Exception as e:
        logger.error(f'Error in HACCP dashboard: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('main.dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/ontvangst', methods=['GET', 'POST'])
@login_required 
def ontvangst(chef_naam):
    """HACCP Ontvangstcontrole"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
        
    cur = conn.cursor(dictionary=True)

    try:
        # Haal leveranciers op
        cur.execute("""
            SELECT * FROM leveranciers 
            WHERE chef_id = %s 
            ORDER BY naam
        """, (session['chef_id'],))
        leveranciers = cur.fetchall()

        if request.method == 'POST':
            # Valideer en verwerk form data
            leverancier_id = request.form.get('leverancier_id')
            product = request.form.get('product')
            temperatuur = request.form.get('temperatuur')
            verpakking_ok = request.form.get('verpakking_ok') == 'true'
            houdbaarheid_ok = request.form.get('houdbaarheid_ok') == 'true'  
            visueel_ok = request.form.get('visueel_ok') == 'true'
            datum_tijd = request.form.get('datum_tijd')
            opmerking = request.form.get('opmerking')
            actie = request.form.get('actie')

            try:
                cur.execute("""
                    INSERT INTO haccp_ontvangst (
                        chef_id, leverancier_id, product, temperatuur,
                        verpakking_ok, houdbaarheid_ok, visueel_ok,
                        datum_tijd, opmerking, actie_ondernomen
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session['chef_id'], leverancier_id, product, temperatuur,
                    verpakking_ok, houdbaarheid_ok, visueel_ok,
                    datum_tijd, opmerking, actie
                ))
                conn.commit()
                
                flash("Ontvangstcontrole succesvol opgeslagen!", "success")
                return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))

            except Exception as e:
                conn.rollback()
                logger.error(f'Error saving ontvangst: {str(e)}')
                flash("Fout bij opslaan van ontvangstcontrole.", "danger")

        return render_template('haccp/ontvangst.html',
                            chef_naam=chef_naam,
                            leveranciers=leveranciers)

    except Exception as e:
        logger.error(f'Error in ontvangst route: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
        
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/temperatuur', methods=['GET', 'POST'])
@login_required
def temperatuur(chef_naam):
    """HACCP Temperatuurcontrole"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
        
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            locatie = request.form.get('locatie')
            temperatuur = request.form.get('temperatuur')
            streefwaarde = request.form.get('streefwaarde')
            datum_tijd = request.form.get('datum_tijd')
            opmerking = request.form.get('opmerking')
            actie = request.form.get('actie')

            if not all([locatie, temperatuur, streefwaarde, datum_tijd]):
                flash("Alle verplichte velden moeten worden ingevuld.", "danger")
                return render_template('haccp/temperatuur.html', 
                                    chef_naam=chef_naam)

            try:
                cur.execute("""
                    INSERT INTO haccp_temperatuur (
                        chef_id, locatie, temperatuur, streefwaarde,
                        datum_tijd, opmerking, actie_ondernomen
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    session['chef_id'], locatie, temperatuur, streefwaarde,
                    datum_tijd, opmerking, actie
                ))
                conn.commit()
                flash("Temperatuurcontrole succesvol opgeslagen!", "success")
                return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))

            except Exception as e:
                conn.rollback()
                logger.error(f'Error saving temperature check: {str(e)}')
                flash("Fout bij opslaan van temperatuurcontrole.", "danger")

        # Get recent temperature readings for reference
        cur.execute("""
            SELECT * FROM haccp_temperatuur
            WHERE chef_id = %s
            ORDER BY datum_tijd DESC
            LIMIT 5
        """, (session['chef_id'],))
        recente_metingen = cur.fetchall()

        return render_template('haccp/temperatuur.html',
                            chef_naam=chef_naam,
                            recente_metingen=recente_metingen)

    except Exception as e:
        logger.error(f'Error in temperatuur route: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
        
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/schoonmaak', methods=['GET'])
@login_required
def schoonmaak_dashboard(chef_naam):
    """HACCP Schoonmaak Dashboard"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
        
    cur = conn.cursor(dictionary=True)

    try:
        # Haal schoonmaak planning op
        cur.execute("""
            SELECT * FROM haccp_schoonmaak_planning
            WHERE chef_id = %s
            ORDER BY locatie, frequentie
        """, (session['chef_id'],))
        planning = cur.fetchall()

        return render_template('haccp/schoonmaak/dashboard.html',
                            chef_naam=chef_naam,
                            planning=planning)

    except Exception as e:
        logger.error(f'Error in schoonmaak dashboard: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('haccp.dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/schoonmaak/planning/new', methods=['GET', 'POST'])
@login_required
def new_schoonmaak_planning(chef_naam):
    """Nieuwe schoonmaak planning toevoegen"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error.", "danger")
            return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))
            
        cur = conn.cursor(dictionary=True)

        try:
            locatie = request.form.get('locatie')
            frequentie = request.form.get('frequentie')
            middel = request.form.get('middel')
            instructie = request.form.get('instructie')

            if not all([locatie, frequentie, middel]):
                flash("Alle verplichte velden moeten worden ingevuld.", "danger")
                return render_template('haccp/schoonmaak/new_planning.html',
                                    chef_naam=chef_naam)

            cur.execute("""
                INSERT INTO haccp_schoonmaak_planning
                (chef_id, locatie, frequentie, middel, instructie)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['chef_id'], locatie, frequentie, middel, instructie))
            
            conn.commit()
            flash("Schoonmaak planning toegevoegd!", "success")
            return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))

        except Exception as e:
            conn.rollback()
            logger.error(f'Error saving cleaning schedule: {str(e)}')
            flash("Fout bij opslaan van schoonmaak planning.", "danger")
            return render_template('haccp/schoonmaak/new_planning.html',
                                chef_naam=chef_naam)
        finally:
            cur.close()
            conn.close()

    return render_template('haccp/schoonmaak/new_planning.html',
                         chef_naam=chef_naam)

@bp.route('/<chef_naam>/schoonmaak/planning/<int:planning_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_schoonmaak_planning(chef_naam, planning_id):
    """Schoonmaak planning bewerken"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error.", "danger")
        return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))
        
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == 'POST':
            locatie = request.form.get('locatie')
            frequentie = request.form.get('frequentie')
            middel = request.form.get('middel')
            instructie = request.form.get('instructie')

            if not all([locatie, frequentie, middel]):
                flash("Alle verplichte velden moeten worden ingevuld.", "danger")
                return redirect(url_for('haccp.edit_schoonmaak_planning', 
                                      chef_naam=chef_naam, planning_id=planning_id))

            cur.execute("""
                UPDATE haccp_schoonmaak_planning 
                SET locatie = %s, frequentie = %s, middel = %s, instructie = %s
                WHERE planning_id = %s AND chef_id = %s
            """, (locatie, frequentie, middel, instructie, planning_id, session['chef_id']))
            
            conn.commit()
            flash("Schoonmaak planning bijgewerkt!", "success")
            return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))

        # Haal bestaande planning op
        cur.execute("""
            SELECT * FROM haccp_schoonmaak_planning
            WHERE planning_id = %s AND chef_id = %s
        """, (planning_id, session['chef_id']))
        planning = cur.fetchone()

        if not planning:
            flash("Planning niet gevonden.", "danger")
            return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))

        return render_template('haccp/schoonmaak/edit_planning.html',
                            chef_naam=chef_naam,
                            planning=planning)

    except Exception as e:
        logger.error(f'Error editing cleaning schedule: {str(e)}')
        flash("Er is een fout opgetreden.", "danger")
        return redirect(url_for('haccp.schoonmaak_dashboard', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

@bp.route('/<chef_naam>/schoonmaak/planning/<int:planning_id>/delete', methods=['POST'])
@login_required
def delete_schoonmaak_planning(chef_naam, planning_id):
    """Schoonmaak planning verwijderen"""
    if session['chef_naam'] != chef_naam:
        return jsonify({'success': False, 'error': 'Geen toegang'}), 403

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database verbindingsfout'}), 500

    cur = conn.cursor()
    try:
        # Verwijder planning
        cur.execute("""
            DELETE FROM haccp_schoonmaak_planning
            WHERE planning_id = %s AND chef_id = %s
        """, (planning_id, session['chef_id']))
        
        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        logger.error(f'Error deleting cleaning schedule: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()
