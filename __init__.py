from flask import Flask
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
from .routes import routes
from .database import get_db_connection  # Add this import
import traceback

def create_app():
    app = Flask(__name__)
    load_dotenv()
    
    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/echef.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('eChef startup')

    # Configure database
    try:
        app.config['DB_HOST'] = os.getenv('DB_HOST')
        app.config['DB_NAME'] = os.getenv('DB_NAME')
        app.config['DB_USER'] = os.getenv('DB_USER')
        app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
        app.config['DB_PORT'] = os.getenv('DB_PORT')
        app.logger.info('Database configuration loaded')
    except Exception as e:
        app.logger.error(f"Error loading database configuration: {e}")
        raise

    # Register the routes Blueprint
    try:
        app.register_blueprint(routes, url_prefix='/')
        app.logger.info('Blueprint registered successfully')
    except Exception as e:
        app.logger.error(f"Error registering blueprint: {e}")
        raise

    # Test database connection
    try:
        with get_db_connection() as conn:
            app.logger.info('Database connection established successfully')
    except Exception as e:
        app.logger.error(f"Error establishing database connection: {e}")
        app.logger.error(traceback.format_exc())
        raise

    # Error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"An error occurred: {e}")
        app.logger.error(traceback.format_exc())
        return "An internal error occurred.", 500

    return app
