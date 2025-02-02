from flask import Blueprint, render_template
from flask_wtf import FlaskForm

main = Blueprint('main', __name__)

# Verwijder de quickstart route hier aangezien deze nu in de quickstart blueprint zit