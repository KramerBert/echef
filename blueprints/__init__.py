from flask import Blueprint
from .main.routes import main
from .quickstart.routes import bp as quickstart_bp

# Blueprints worden hier geregistreerd
# These blueprints need to be imported in create_app()