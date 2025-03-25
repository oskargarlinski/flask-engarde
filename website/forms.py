from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError
import re


def strong_password(form, field):
    password = field.data

    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError(
            "Password must include at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValidationError(
            "Password must include at least one lowercase letter.")
    if not re.search(r'\d', password):
        raise ValidationError("Password must include at least one number.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(
            "Password must include at least one special character.")


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


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(
        message="Email is required."), Email(message="Please enter a valid email address.")])
    password = PasswordField('Password', validators=[
                             DataRequired(message="Password is required.")])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class BaseProductForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    description = StringField("Description", validators=[DataRequired()])
    image = FileField("Product Image", validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])
    price = FloatField("Price (£)", validators=[DataRequired()])
    environmental_impact = FloatField(
        "Environmental Impact (kg CO₂)", validators=[DataRequired()])


class WeaponForm(BaseProductForm):
    blade_type = SelectField("Blade Type", choices=[
        ('', 'Select'), ('Foil', 'Foil'), ('Epee', 'Épée'), ('Sabre', 'Sabre')
    ], validators=[DataRequired()])
    certification = StringField("Certification")
    submit = SubmitField("Add Weapon")


class ApparelForm(BaseProductForm):
    material = StringField("Material")
    certification = StringField("Certification")
    newton_rating = IntegerField("Newton Rating")
    submit = SubmitField("Add Apparel")


class GloveForm(BaseProductForm):
    certification = StringField("Certification")
    submit = SubmitField("Add Glove")


class FootwearForm(BaseProductForm):
    submit = SubmitField("Add Footwear")
