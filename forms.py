from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Optional
from wtforms import ValidationError
from flask_wtf import RecaptchaField

class RegisterForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Herhaal wachtwoord', validators=[DataRequired(), EqualTo('wachtwoord', message='Wachtwoorden moeten overeenkomen')])
    terms = BooleanField('Ik ga akkoord met de <a href="/terms" target="_blank">algemene voorwaarden</a>', validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField('Registreer')

    def validate_email(self, email):
        from app import Chef
        chef = Chef.query.filter_by(email=email.data).first()
        if chef:
            raise ValidationError('Dit e-mailadres is al in gebruik.')

class LeverancierForm(FlaskForm):
    leverancier_naam = StringField('Naam', validators=[DataRequired()])
    leverancier_contact = StringField('Contact')
    leverancier_telefoon = StringField('Telefoon')
    leverancier_email = StringField('Email', validators=[Email(), Optional()])
    submit = SubmitField('Toevoegen')

class EenheidForm(FlaskForm):
    nieuwe_eenheid = StringField('Naam', validators=[DataRequired()])
    submit = SubmitField('Toevoegen')

class CategorieForm(FlaskForm):
    nieuwe_categorie = StringField('Naam', validators=[DataRequired()])
    submit = SubmitField('Toevoegen')

class DishCategoryForm(FlaskForm):
    nieuwe_dish_category = StringField('Naam', validators=[DataRequired()])
    volgorde = IntegerField('Volgorde', validators=[Optional()])
    submit = SubmitField('Toevoegen')
