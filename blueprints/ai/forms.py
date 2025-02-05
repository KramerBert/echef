from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class RecipeGenerationForm(FlaskForm):
    prompt = TextAreaField('Beschrijf het gerecht dat je wilt maken', 
                          validators=[DataRequired()])
    cuisine = StringField('Keuken (bijv. Frans, Italiaans)', 
                         validators=[DataRequired()])
    dietary = StringField('Dieetwensen (optioneel)')
    submit = SubmitField('Genereer Recept')
