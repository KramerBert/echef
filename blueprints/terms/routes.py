from flask import render_template, Blueprint
from flask_wtf import FlaskForm

bp = Blueprint('terms', __name__, template_folder='templates')

@bp.route('/')
def terms_index():
    return render_template('terms.html', form=FlaskForm())
