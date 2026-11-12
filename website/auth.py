import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from . import db
from .models import User
from .security import verify_password

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        # Try the original spelling first, including unusual legacy addresses.
        user = User.query.filter_by(email=email).first()
        if user is None and email != email.strip():
            user = User.query.filter_by(email=email.strip()).first()
        if user and verify_password(user.password, password):
            login_user(user, remember=True)
            flash('Welcome back. Your ideas are right here.', 'success')
            return redirect(url_for('views.home'))
        flash('Email or password is incorrect.', 'error')
    return render_template('login.html')


@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    # Keep the original URL; GET confirms and a CSRF-protected POST logs out.
    if request.method == 'POST':
        logout_user()
        return redirect(url_for('auth.login'))
    return render_template('logout.html')


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('firstName', '').strip()
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')
        if not (4 <= len(email) <= 150) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            flash('Enter a valid email address (up to 150 characters).', 'error')
        elif not 2 <= len(first_name) <= 150:
            flash('Your first name must be between 2 and 150 characters.', 'error')
        elif password1 != password2:
            flash('Passwords do not match.', 'error')
        elif not 7 <= len(password1) <= 1024:
            flash('Use a password between 7 and 1,024 characters.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
        else:
            user = User(email=email, first_name=first_name,
                        password=generate_password_hash(password1))
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('An account with this email already exists.', 'error')
            else:
                login_user(user, remember=True)
                flash('Your notebook is ready. Make yourself at home.', 'success')
                return redirect(url_for('views.home'))
    return render_template('sign_up.html')
