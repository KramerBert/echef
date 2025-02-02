from flask import Blueprint, render_template, current_app
from flask_wtf import FlaskForm

bp = Blueprint('quickstart', __name__, url_prefix='/quickstart')

@bp.route('/')
def quickstart():
    """Show the quickstart guide page"""
    return render_template('quickstart/quickstart.html', form=FlaskForm())
