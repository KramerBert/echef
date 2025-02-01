from flask import Flask
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
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

    # Import routes after app is created to avoid circular imports
    from .routes import routes
    app.register_blueprint(routes)

    # Error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"An error occurred: {e}")
        app.logger.error(traceback.format_exc())
        return "An internal error occurred.", 500

    return app