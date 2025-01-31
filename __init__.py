from flask import Flask
from .routes import routes

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Verander dit in productie
    
    # Register the routes Blueprint
    app.register_blueprint(routes, url_prefix='/')

    return app
