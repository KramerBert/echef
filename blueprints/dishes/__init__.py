from flask import Blueprint

bp = Blueprint('dishes', __name__)

from . import routes
