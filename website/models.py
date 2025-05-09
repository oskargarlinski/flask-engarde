from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, validates
from flask_login import UserMixin
from wtforms.validators import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    
    parent = db.relationship('Category', backref='children', remote_side=[id] )
    products = db.relationship('Product', backref='category', lazy=True)
    
    

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=True)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    environmental_impact = db.Column(db.Float, nullable=True)
    stock = db.Column(db.Integer, nullable=True)
    image_filename = db.Column(db.String(255))
    is_variant_parent = db.Column(db.Boolean, default=False)

    options = db.relationship(
        'VariantOption', backref='product', cascade="all, delete")
    variants = db.relationship(
        'ProductVariant', backref='product', cascade="all, delete")


class VariantOption(db.Model):
    __tablename__ = 'variant_options'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey(
        'products.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # e.g. "Size", "Hand"
    values = db.relationship(
        'VariantValue', backref='option', cascade="all, delete")


class VariantValue(db.Model):
    __tablename__ = 'variant_values'

    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey(
        'variant_options.id'), nullable=False)
    value = db.Column(db.String(50), nullable=False)


class ProductVariant(db.Model):
    __tablename__ = 'product_variants'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey(
        'products.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    price = db.Column(db.Float, nullable=False)
    environmental_impact = db.Column(db.Float, nullable=True)
    stock = db.Column(db.Integer, default=0)

    values = db.relationship(
        'VariantValue', secondary='variant_combinations', backref='variants', lazy='joined', overlaps="combinations")


class VariantCombination(db.Model):
    __tablename__ = 'variant_combinations'
    variant_id = db.Column(db.Integer, db.ForeignKey(
        'product_variants.id'), primary_key=True)
    value_id = db.Column(db.Integer, db.ForeignKey(
        'variant_values.id'), primary_key=True)

    variant = db.relationship('ProductVariant', backref=db.backref(
        'combinations', cascade='all, delete-orphan'), overlaps="values,variants")
    value = db.relationship('VariantValue', backref=db.backref(
        'combinations', cascade='all, delete-orphan'), overlaps="values,variants")


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    total_impact = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    items = db.relationship(
        "OrderItem", backref="order", cascade="all, delete")

    @validates('impact')
    def round_total_impact(self, key, value):
        return round(value, 2)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey(
        'orders.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey(
        'product_variants.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    impact = db.Column(db.Float, nullable=False)

    variant = db.relationship('ProductVariant')
    product = db.relationship('Product')

    @validates('impact')
    def round_impact(self, key, value):
        return round(value, 2)
