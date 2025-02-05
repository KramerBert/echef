from flask import Blueprint

ai_blueprint = Blueprint('ai', __name__, url_prefix='/ai',
                        template_folder='templates')

from . import routes  # Import routes after blueprint creation
