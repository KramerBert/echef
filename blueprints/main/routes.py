from flask import Blueprint, render_template
from flask_wtf import FlaskForm

main = Blueprint('main', __name__, url_prefix='')

@main.route('/quickstart')
def quickstart():
    """Show the quickstart guide page"""
    return render_template('main/quickstart.html', form=FlaskForm())