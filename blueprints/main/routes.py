from flask import Blueprint, render_template
from flask_wtf import FlaskForm

main = Blueprint('main', __name__)

@main.route('/quickstart')
def quickstart():    # Deze functienaam wordt gebruikt in url_for()
    """Show the quickstart guide page"""
    return render_template('main/quickstart.html', form=FlaskForm())