from flask import Flask
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler

def create_app():
    app = Flask(__name__)
    load_dotenv()
    
<<<<<<< HEAD
    # Register the routes Blueprint
    app.register_blueprint(routes, url_prefix='/')

=======
    # Configure logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Configureer file handler
    file_handler = RotatingFileHandler('logs/echef.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Voeg handlers toe aan de app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('E-Chef startup')
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    
>>>>>>> 869cdb8e8fc7f57aa73743e6536e9b86a6433c8a
    return app
