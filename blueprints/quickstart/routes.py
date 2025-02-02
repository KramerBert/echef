from flask import Blueprint, render_template
from flask_wtf import FlaskForm

# Enkel één blueprint definitie behouden
bp = Blueprint('quickstart', __name__, url_prefix='/quickstart')

@bp.route('/')
def index():
    """Show the quickstart guide page"""
    return render_template('quickstart/quickstart.html', form=FlaskForm())

# Verwijder de volgende dubbele blueprint definitie:
# from flask import Blueprint
# quickstart = Blueprint('quickstart', __name__, url_prefix='/quickstart')
#
# @quickstart.route('/')
# def index():
#     return "Welcome to Quickstart!"