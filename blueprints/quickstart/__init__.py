from flask import Blueprint

bp = Blueprint('quickstart', __name__, template_folder='templates')

from . import routes
