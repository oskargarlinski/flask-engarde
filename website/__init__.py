from flask import Flask
from .models import db, User
from os import path
from flask_login import LoginManager

DB_NAME = 'database.db'
UPLOAD_FOLDER = 'website/static/images/products'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'ANGRY CHIHUAHUA'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_NAME
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    db.init_app(app)

    from .views import views
    from .auth import auth
    from .admin import admin

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(admin, url_prefix='/')
    
    
    @app.template_filter('min_price')
    def min_price(variants):
        return min((v.price for v in variants if v.price is not None), default=None)

    @app.template_filter('min_impact')
    def min_impact(variants):
        return min((v.environmental_impact for v in variants if v.environmental_impact is not None), default=None)



    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
