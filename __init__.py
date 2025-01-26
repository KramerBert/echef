from flask import Flask
from .routes import routes

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Verander dit in productie
    
    app.register_blueprint(routes)
    
    return app
