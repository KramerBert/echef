from flask import Blueprint, render_template
from flask_wtf import FlaskForm

bp = Blueprint('instructions', __name__, url_prefix='/instructions')

@bp.route('/')
def index():
    return render_template('instructions/instruction.html') 