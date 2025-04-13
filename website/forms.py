from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, FieldList, FormField, HiddenField, Form, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError, NumberRange, Optional
import re
from datetime import datetime


def validate_expiry_date(form, field):
    try:
        exp_str = field.data.strip()
        if '/' not in exp_str:
            raise ValidationError("Use MM/YY format.")

        month, year = exp_str.split('/')
        month = int(month)
        year = int(year)

        if year < 100:
            year += 2000

        if not 1 <= month < 13:
            raise ValidationError("Invalid month.")

        now = datetime.now()
        expiry = datetime(year, month, 1)

        if expiry < now.replace(day=1):
            raise ValidationError("Card has expired.")

    except:
        raise ValidationError("Invalid date format.")


def validate_credit_card(form, field):
    cleaned = re.sub(r'[\s\-]', '', field.data)
    if not cleaned.isdigit() or len(cleaned) != 16:
        raise ValidationError("Card number must be a 16-digit number.")


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
    environmental_impact = FloatField(
        "Environmental Impact (kg CO₂)", validators=[Optional()])
    stock = IntegerField("Stock", default=0)
    submit = SubmitField("Create Product")

    def validate_price(self, field):
        if not self.is_variant_parent.data:
            if field.data is None:
                raise ValidationError(
                    "Price is required for non-variant products. ")

    def validate_environmental_impact(self, field):
        if not self.is_variant_parent.data:
            if field.data is None:
                raise ValidationError(
                    "Environmental Impact is required for non-variant products. ")


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
        DataRequired(), validate_credit_card])
    expiry_date = StringField("Expiry Date (MM/YY)",
                              validators=[DataRequired(), validate_expiry_date])
    cvv = StringField("CVV", validators=[DataRequired(), Regexp(
        r'^\d{3,4}$', message="CVV must be 3 or 4 digits.")])
    next = SubmitField("Review Order")


class ReviewForm(FlaskForm):
    submit = SubmitField("Place Order")


class SingleVariantForm(Form):
    combo_str = HiddenField()
    price = FloatField("Price", validators=[
                       DataRequired(), NumberRange(min=0)])
    environmental_impact = FloatField("Environmental Impact", validators=[
                                      DataRequired(), NumberRange(min=0)])
    stock = IntegerField("Stock", validators=[
                         DataRequired(), NumberRange(min=0)])


class WizardVariantsForm(FlaskForm):
    variants = FieldList(FormField(SingleVariantForm))
    submit = SubmitField("Save All Variants")


class WizardStep3OptionForm(Form):
    option_name = HiddenField()
    values_str = StringField("Values", validators=[
                             DataRequired(), Length(max=200)])


class WizardStep3Form(FlaskForm):
    options = FieldList(FormField(WizardStep3OptionForm))
    submit = SubmitField("Next")


class CategoryForm(FlaskForm):
    parent_id = SelectField("Parent Category", coerce=int, choices=[])
    name = StringField("Name", validators=[DataRequired()])
    slug = StringField("Slug", validators=[DataRequired()])
    submit = SubmitField("Save Category")


class PricingRuleForm(FlaskForm):
    option_name = SelectField("Option")
    option_value = SelectField("Value")
    match_conditions = HiddenField()  # gets auto-filled via JS
    base_price = FloatField("Base Price (£)")
    base_impact = FloatField("Base Environmental Impact")
    stock = IntegerField("Stock")

    class Meta:
        csrf = False


class ModifierForm(FlaskForm):
    option_name = SelectField("Option")
    option_value = SelectField("Value")
    value_name = HiddenField()  # Gets populated via JS
    price_modifier = FloatField("Price Modifier")
    impact_modifier = FloatField("Impact Modifier")
    stock_modifier = IntegerField("Stock Modifier", default=0)

    class Meta:
        csrf = False


class RuleWizardForm(FlaskForm):
    pricing_rules = FieldList(FormField(PricingRuleForm), min_entries=1)
    modifiers = FieldList(FormField(ModifierForm), min_entries=1)
    submit = SubmitField("Continue to Variants")
