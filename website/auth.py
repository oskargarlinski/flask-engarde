from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    return render_template("login.html", active_page='login')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for(auth.login))


@auth.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    return render_template("sign_up.html", active_page='sign_up')
