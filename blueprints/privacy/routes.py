from flask import render_template
from . import bp

@bp.route('/privacy')
def privacy():
    return render_template('privacy.html')  # Verwijder 'privacy/' prefix
