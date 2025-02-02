import os
from flask import Flask  # Toegevoegd

# Maak de app-instantie als deze nog niet bestaat
app = Flask(__name__)  # Toegevoegd

# Voeg deze regel toe om SECURITY_PASSWORD_SALT in te stellen
app.config['SECURITY_PASSWORD_SALT'] = os.environ['SECURITY_PASSWORD_SALT']
