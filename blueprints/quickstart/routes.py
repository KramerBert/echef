from flask import Blueprint, render_template
from flask_wtf import FlaskForm

# Verwijder template_folder omdat we relative paths gebruiken
bp = Blueprint('quickstart', __name__, url_prefix='/quickstart')

@bp.route('/')
def index():
    """Show the quickstart guide page"""
    return render_template('quickstart/quickstart.html', form=FlaskForm())
