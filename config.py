import os
from flask import Flask  # Toegevoegd

# Maak de app-instantie als deze nog niet bestaat
app = Flask(__name__)  # Toegevoegd

# Voeg deze regel toe om SECURITY_PASSWORD_SALT in te stellen
SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT')

if not SECURITY_PASSWORD_SALT:
    print("Error: SECURITY_PASSWORD_SALT is missing")
