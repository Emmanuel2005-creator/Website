"""Application factory and environment-based configuration."""
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///database.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '').lower() == 'true',
        REMEMBER_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '').lower() == 'true',
        MAX_CONTENT_LENGTH=128 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        raise RuntimeError('Set the SECRET_KEY environment variable before starting the app.')

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    from .auth import auth
    from .views import views
    from .models import User

    app.register_blueprint(views)
    app.register_blueprint(auth)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to open your notebook.'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.endpoint == 'views.delete_note':
            return jsonify(error='Please log in before deleting a note.'), 401
        from flask import flash, redirect, url_for
        flash(login_manager.login_message, 'error')
        return redirect(url_for('auth.login'))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = 'Your form has expired or could not be verified. Reload the page and try again.'
        if request.endpoint == 'views.delete_note':
            return jsonify(error=message), 400
        return render_template('error.html', code=400, message=message), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.endpoint == 'views.delete_note':
            return jsonify(error=error.description), error.code
        return render_template('error.html', code=error.code, message=error.description), error.code

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.error('A database operation failed.', exc_info=True)
        message = 'We could not save your changes. Please try again.'
        if request.endpoint == 'views.delete_note':
            return jsonify(error=message), 500
        return render_template('error.html', code=500, message=message), 500

    @app.context_processor
    def template_user():
        return {'user': current_user}

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self'; font-src 'self'; base-uri 'self'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        return response

    # Only creates missing tables; never resets or migrates existing data.
    with app.app_context():
        db.create_all()
    return app
