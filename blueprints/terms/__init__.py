from flask import Blueprint

bp = Blueprint('terms', __name__, template_folder='templates')

from . import routes
