from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class RegisterForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    confirm_password = PasswordField('Bevestig Wachtwoord', validators=[DataRequired(), EqualTo('wachtwoord')])
    submit = SubmitField('Registreren')

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    wachtwoord = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Inloggen')

# Add any new forms here
class NewForm(FlaskForm):
    field1 = StringField('Field1', validators=[DataRequired()])
    field2 = StringField('Field2', validators=[DataRequired()])
    submit = SubmitField('Submit')
