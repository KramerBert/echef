from flask import Blueprint

bp = Blueprint('suppliers', __name__)

from . import routes
