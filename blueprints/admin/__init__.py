from flask import Blueprint
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

@bp.context_processor
def utility_processor():
    """Add utility functions to template context"""
    def now():
        return datetime.now()
    return dict(now=now)

from . import routes
