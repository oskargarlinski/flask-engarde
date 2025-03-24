from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from . import db
import json

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template("home.html", active_page='home')
