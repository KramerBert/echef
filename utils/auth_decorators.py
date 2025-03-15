from functools import wraps
from flask import session, redirect, url_for, flash

def admin_required(f):
    """Decorator to ensure user is an admin chef"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'chef_id' not in session or not session.get('is_admin'):
            flash("Je moet beheerdersrechten hebben om deze pagina te bekijken.", "danger")
            return redirect(url_for('dashboard', chef_naam=session.get('chef_naam', '')))
        return f(*args, **kwargs)
    return decorated_function
