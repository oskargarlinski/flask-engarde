from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError
import re


def strong_password(form, field):
    password = field.data

    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError( "Password must include at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValidationError( "Password must include at least one lowercase letter.")
    if not re.search(r'\d', password):
        raise ValidationError("Password must include at least one number.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError( "Password must include at least one special character.")


class SignupForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Regexp(
        '^[A-Za-zÀ-ÿ\'\- ]+$', message="Name must contain only letters, spaces, or hyphens.")])
    last_name = StringField("Last Name", validators=[DataRequired(), Regexp(
        r"^[A-Za-zÀ-ÿ'\- ]+$", message="Only letters, spaces, hyphens, and apostrophes allowed.")])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
                             DataRequired(message="Password is required."), strong_password])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(message="Please confirm your password."), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign Up')
