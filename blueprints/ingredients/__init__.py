from flask import Blueprint

bp = Blueprint('ingredients', __name__)

from . import routes
