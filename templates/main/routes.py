from flask import Blueprint, render_template
from flask_wtf import FlaskForm

main = Blueprint('main', __name__, template_folder='templates')

@main.route('/quickstart')
def quickstart():
    form = FlaskForm()
    return render_template('main/quickstart.html', form=form)