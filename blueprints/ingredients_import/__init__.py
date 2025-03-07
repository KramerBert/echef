from flask import Blueprint

bp = Blueprint('ingredients_import', __name__, url_prefix='/ingredients/import', template_folder='templates')

from . import routes
