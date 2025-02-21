from flask import render_template, session, flash, redirect, url_for
from flask_wtf import FlaskForm
from . import bp
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'chef_id' not in session:
            flash("Geen toegang. Log opnieuw in.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard/<chef_naam>')
@login_required
def dashboard(chef_naam):
    """Main dashboard page after login"""
    if session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
    if 'chef_id' not in session or session['chef_naam'] != chef_naam:
        flash("Geen toegang. Log opnieuw in.", "danger")
        return redirect(url_for('auth.login'))
            
    return render_template('dashboard.html', chef_naam=chef_naam, form=FlaskForm())
