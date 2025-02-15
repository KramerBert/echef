from flask import Blueprint, render_template

bp = Blueprint('instructions', __name__, url_prefix='/instructions')

@bp.route('/')
def index():
    return render_template('instructions/instruction.html')  # Let op: template pad wordt relatief aan de app templates folder
