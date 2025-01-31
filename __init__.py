from flask import Flask
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
from .routes import routes  # Add this import statement

def create_app():
    app = Flask(__name__)
    load_dotenv()
    
    # Register the routes Blueprint
    app.register_blueprint(routes, url_prefix='/')

    # Error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"An error occurred: {e}")
        return "An internal error occurred.", 500

    return app
