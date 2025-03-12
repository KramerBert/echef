from flask import Blueprint

bp = Blueprint('takenboek', __name__)

from . import routes
