from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class RecipeGenerationForm(FlaskForm):
    prompt = TextAreaField('Beschrijf het gerecht dat je wilt maken', 
                          validators=[DataRequired()], default="Hier je tekst")
    cuisine = StringField('Keuken (bijv. Frans, Italiaans)', 
                         default="")
    dietary = StringField('Dieetwensen (optioneel)', default="")
    submit = SubmitField('Genereer Recept')
