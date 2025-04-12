from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, FieldList, FormField, HiddenField, Form, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError, NumberRange, Optional
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
    category = SelectField("Category", coerce=int, validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    description = StringField("Description", validators=[DataRequired()])
    image = FileField("Product Image", validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])


class AdminProductForm(BaseProductForm):
    is_variant_parent = BooleanField("This product has variants", default=True)

    price = FloatField("Price (£)", validators=[Optional()])
    environmental_impact = FloatField("Environmental Impact (kg CO₂)", validators=[Optional()])
    stock = IntegerField("Stock", default=0)
    submit = SubmitField("Create Product")
    
    def validate_price(self, field):
        if not self.is_variant_parent.data:
            if field.data is None:
                raise ValidationError("Price is required for non-variant products. ")
            
    def validate_environmental_impact(self, field):
        if not self.is_variant_parent.data:
            if field.data is None:
                raise ValidationError("Environmental Impact is required for non-variant products. ")


class SingleOptionForm(FlaskForm):
    option_name = StringField("Option", validators=[
                              DataRequired(), Length(max=50)])

    class Meta:
        csrf = False


class VariantOptionForm(FlaskForm):
    options = FieldList(FormField(SingleOptionForm), min_entries=1)
    submit = SubmitField("Save Options")


class ValueEntryForm(Form):
    value = StringField("Value", validators=[DataRequired(), Length(max=50)])


class VariantValueForm(FlaskForm):
    option_id = HiddenField("Option ID")
    values = FieldList(FormField(ValueEntryForm), min_entries=1)
    submit = SubmitField("Save Values")


class VariantValueSubForm(FlaskForm):
    values = StringField("Values (comma-separated)",
                         validators=[DataRequired()])


class ProductVariantForm(FlaskForm):
    class Meta:
        csrf = False

    sku = StringField("SKU", validators=[DataRequired(), Length(
        max=50)], render_kw={"readonly": True})
    price = FloatField("Price", validators=[DataRequired()])
    environmental_impact = FloatField(
        "Environmental Impact (kg CO₂)", validators=[DataRequired()])
    stock = IntegerField("Stock", validators=[
                         DataRequired(), NumberRange(min=0)])


class AddToCartForm(FlaskForm):
    variant_id = HiddenField()
    product_id = HiddenField()
    quantity = IntegerField("Quantity", default=1, validators=[
        DataRequired(),
        NumberRange(min=1, message="Must be at least 1")
    ])
    submit = SubmitField("Add to Cart")


class ShippingForm(FlaskForm):
    first_name = StringField("First Name", validators=[
                             DataRequired(), Length(max=100)])
    last_name = StringField("Last Name", validators=[
                            DataRequired(), Length(max=100)])
    shipping_address = StringField(
        "Address", validators=[DataRequired(), Length(max=255)])
    city = StringField("City", validators=[DataRequired()])
    country = SelectField("Country", choices=[
        ("England", "England"),
        ("Scotland", "Scotland"),
        ("Wales", "Wales"),
        ("Northern Ireland", "Northern Ireland")
    ], validators=[DataRequired()])
    postal_code = StringField("Postcode", validators=[DataRequired()])
    next = SubmitField("Continue to Payment")


class PaymentForm(FlaskForm):
    card_number = StringField("Card Number", validators=[
                              DataRequired(), Length(min=16, max=16)])
    expiry_date = StringField("Expiry Date", validators=[DataRequired()])
    cvv = StringField("CVV", validators=[DataRequired(), Length(min=3, max=4)])
    next = SubmitField("Review Order")


class ReviewForm(FlaskForm):
    submit = SubmitField("Place Order")

class SingleVariantForm(Form):
    combo_str = HiddenField()
    price = FloatField("Price", validators=[DataRequired(), NumberRange(min=0)])
    environmental_impact = FloatField("Environmental Impact", validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField("Stock", validators=[DataRequired(), NumberRange(min=0)])
    
class WizardVariantsForm(FlaskForm):
    variants = FieldList(FormField(SingleVariantForm))
    submit = SubmitField("Save All Variants")
    
class WizardStep3OptionForm(Form):
    option_name = HiddenField()
    values_str = StringField("Values", validators=[DataRequired(), Length(max=200)])


class WizardStep3Form(FlaskForm):
    options = FieldList(FormField(WizardStep3OptionForm))
    submit = SubmitField("Next")
    
class CategoryForm(FlaskForm):
    parent_id = SelectField("Parent Category", coerce=int, choices=[])
    name = StringField("Name", validators=[DataRequired()])
    slug = StringField("Slug", validators=[DataRequired()])
    submit= SubmitField("Save Category")