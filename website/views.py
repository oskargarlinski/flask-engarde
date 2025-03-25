from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from . import db
import json

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template("home.html", active_page='home')


@views.route('/shop')
def shop():
    return render_template('shop.html', active_page='shop')


@views.route('/contact')
def contact():
    return render_template('contact.html', active_page='contact')
