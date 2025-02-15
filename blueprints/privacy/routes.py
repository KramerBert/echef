from flask import render_template, Blueprint
from flask_wtf import FlaskForm

bp = Blueprint('privacy', __name__, template_folder='templates')

@bp.route('/')
def privacy_index():
    return render_template('privacy.html', form=FlaskForm())
