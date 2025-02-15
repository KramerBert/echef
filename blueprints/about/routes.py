from flask import Blueprint, render_template
from flask_wtf import FlaskForm

bp = Blueprint('about', __name__, template_folder='templates')

@bp.route('/about')
def about():
    return render_template('about/about.html', form=FlaskForm())
