from flask import Blueprint, render_template
from flask_wtf import FlaskForm

bp = Blueprint('quickstart', __name__)

@bp.route('/')
def index():
    """Show the quickstart guide page"""
    return render_template('quickstart/quickstart.html', form=FlaskForm())
