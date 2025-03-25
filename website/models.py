from flask_sqlalchemy import SQLAlchemy
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')


class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    environmental_impact = db.Column(db.Float) # e.g., 12.5 (kg CO2 equivalent)

    __mapper_args__ = {
        'polymorphic_identity': 'product',
        'polymorphic_on': type
    }


class Apparel(Product):
    __tablename__ = 'apparel'

    id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    material = db.Column(db.String(50))
    certification = db.Column(db.String(50))
    newton_rating = db.Column(db.Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'apparel'
    }


class Glove(Product):
    __tablename__ = 'glove'

    id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    certification = db.Column(db.String(50))

    __mapper_args__ = {
        'polymorphic_identity': 'glove'
    }


class Footwear(Product):
    __tablename__ = 'footwear'

    id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'footwear'
    }


class Weapon(Product):
    __tablename__ = 'weapon'

    id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    certification = db.Column(db.String(50))

    # Filtering Fields
    blade_type = db.Column(db.String(20))  # "Foil", "Epee", "Sabre"
    
    __mapper_args__ = {
        'polymorphic_identity': 'weapon'
    }
