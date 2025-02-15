from flask import Blueprint

bp = Blueprint('auth', __name__, template_folder='templates')

from . import routes
from .routes import LoginForm, ForgotPasswordForm, ResetPasswordForm, RegisterForm
from .utils import generate_confirmation_token, confirm_token, send_confirmation_email, send_reset_email, hash_password
