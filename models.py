from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Gerecht(db.Model):
    dish_id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String(100), nullable=False)
    beschrijving = db.Column(db.Text)
    categorie = db.Column(db.String(50))
    bereidingswijze = db.Column(db.Text)
    verkoopprijs = db.Column(db.Float)
    chef_naam = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Ingredient(db.Model):
    ingredient_id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String(100), nullable=False)
    eenheid = db.Column(db.String(20))
    prijs_per_eenheid = db.Column(db.Float)
    categorie = db.Column(db.String(50))

class GerechtIngredient(db.Model):
    gerecht_id = db.Column(db.Integer, db.ForeignKey('gerecht.dish_id'), primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.ingredient_id'), primary_key=True)
    hoeveelheid = db.Column(db.Float, nullable=False)
