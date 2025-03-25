from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from .models import db, User
from .forms import SignupForm, LoginForm

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for("views.home"))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template("login.html", form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    form = SignupForm()
    # Check if user already exists (also handled in form validator for a second layer of security)
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("An account with that email already exists.", "danger")
            return redirect(url_for('auth.sign_up'))

        # Start creating new user
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(first_name=form.first_name.data, last_name=form.last_name.data,
                        email=form.email.data, password_hash=hashed_password)

        # Try and add the user to the database.
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash("Account created successfully! You can now log in.", "success")
            return redirect(url_for("views.home"))
        except Exception as e:
            db.session.rollback()
            flash("Something went wrong while creating your account.", "danger")
            print("DB Error", e)
    return render_template("sign_up.html", form=form)
