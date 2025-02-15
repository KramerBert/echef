from flask import Blueprint

bp = Blueprint('privacy', __name__, template_folder='templates')

from . import routes
