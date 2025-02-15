from flask import render_template, Blueprint
from flask_wtf import FlaskForm

bp = Blueprint('quickstart', __name__, template_folder='templates')

@bp.route('/')
def quickstart_index():
    return render_template('quickstart.html', form=FlaskForm())
