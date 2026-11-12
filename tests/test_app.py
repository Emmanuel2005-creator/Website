import hashlib
import sqlite3

import pytest
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from website import create_app, db
from website.models import Note, User
from website.security import verify_password
from conftest import login, logout, register, token

# Synthetic salted SHA-256 fixture in the original Werkzeug format.
LEGACY_HASH = 'sha256$legacySalt42$ec09e25fe7bb19533c2ed08f239b57723a9b7ed84aca6565def4723ecf600010'


def test_startup_config_and_health(app, client):
    assert not app.debug
    assert app.config['WTF_CSRF_ENABLED']
    assert app.config['SESSION_COOKIE_HTTPONLY']
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}
    assert response.headers['Cache-Control'] == 'no-store'


def test_secret_required(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app()


def test_environment_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('SECRET_KEY', 'environment-only-test-key')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + (tmp_path / 'env.db').as_posix())
    monkeypatch.setenv('COOKIE_SECURE', 'true')
    app = create_app()
    assert app.config['SESSION_COOKIE_SECURE']
    assert app.config['REMEMBER_COOKIE_SECURE']
    assert app.secret_key == 'environment-only-test-key'
    with app.app_context():
        db.engine.dispose()


@pytest.mark.parametrize('path', ['/login', '/sign-up'])
def test_public_routes(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data
    assert b'notebook.svg' in response.data


@pytest.mark.parametrize('path', ['/', '/logout'])
def test_login_required(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location.endswith('/login')


def test_anonymous_delete_is_authenticated(client):
    response = client.post('/delete-note', json={'noteId': 1},
                           headers={'X-CSRFToken': token(client)})
    assert response.status_code == 401
    assert 'log in' in response.json['error']


def test_anonymous_cannot_create_notes(app, client):
    response = client.post('/', data={'csrf_token': token(client), 'note': 'not allowed'})
    assert response.status_code == 302
    assert response.location.endswith('/login')
    with app.app_context():
        assert Note.query.count() == 0


def test_signup_login_logout_and_remember_cookie(app, client):
    page = register(client)
    assert page.status_code == 200
    assert b'Your notebook is ready' in page.data
    with app.app_context():
        user = User.query.one()
        assert user.password.startswith('scrypt:')
        assert check_password_hash(user.password, 'test-password')
    assert client.get_cookie('remember_token') is not None
    assert logout(client).status_code == 302
    assert client.get('/').status_code == 302
    assert b'Welcome back.' in login(client).data
    assert client.get('/').status_code == 200


def test_get_logout_does_not_end_session(client):
    register(client)
    response = client.get('/logout')
    assert response.status_code == 200
    assert b'Ready to step away?' in response.data
    assert client.get('/').status_code == 200


@pytest.mark.parametrize('data, message', [
    ({}, b'valid email'),
    ({'email': 'invalid'}, b'valid email'),
    ({'email': 'a' * 151 + '@example.com'}, b'valid email'),
    ({'firstName': ' '}, b'first name'),
    ({'firstName': 'A' * 151}, b'first name'),
    ({'password2': 'different'}, b'do not match'),
    ({'password1': 'short', 'password2': 'short'}, b'between 7'),
    ({'password1': 'p' * 1025, 'password2': 'p' * 1025}, b'between 7'),
])
def test_registration_validation(app, client, data, message):
    values = {'email': 'alex@example.com', 'firstName': 'Alex',
              'password1': 'test-password', 'password2': 'test-password'}
    if not data:
        values = {}
    values.update(data)
    values['csrf_token'] = token(client, '/sign-up')
    response = client.post('/sign-up', data=values)
    assert response.status_code == 200
    assert message in response.data
    with app.app_context():
        assert User.query.count() == 0


def test_duplicate_registration(client, app):
    register(client)
    logout(client)
    response = register(client)
    assert b'already exists' in response.data
    with app.app_context():
        assert User.query.count() == 1


@pytest.mark.parametrize('email,password', [
    ('alex@example.com', 'wrong'), ('missing@example.com', 'test-password'), ('', ''),
])
def test_login_failure_does_not_authenticate(client, email, password):
    register(client)
    logout(client)
    page = login(client, email, password)
    assert b'Email or password is incorrect.' in page.data
    assert client.get('/').status_code == 302


@pytest.mark.parametrize('stored,password', [
    (LEGACY_HASH, 'legacy-password'),
    (generate_password_hash('legacy-password', method='pbkdf2:sha256:1000'), 'legacy-password'),
    (generate_password_hash('legacy-password'), 'legacy-password'),
])
def test_existing_password_formats(app, client, stored, password):
    with app.app_context():
        db.session.add(User(email='old@example.com', first_name='Existing', password=stored))
        db.session.commit()
    assert b'Welcome back.' in login(client, 'old@example.com', password).data
    with app.app_context():
        assert User.query.one().password == stored


@pytest.mark.parametrize('stored', ['', 'malformed', 'sha256$$invalid', 'sha256$salt$' + '0'*64, 'unsupported$salt$digest'])
def test_malformed_and_wrong_password_hashes(stored):
    assert not verify_password(stored, 'wrong')


def test_legacy_unusual_credentials_remain_usable(app, client):
    # The original registration did not validate email shape or cap passwords.
    password = 'old-password-' * 100
    with app.app_context():
        db.session.add(User(email=' legacy-account ', first_name='Legacy',
                            password=generate_password_hash(password)))
        db.session.commit()
    assert b'Welcome back.' in login(client, ' legacy-account ', password).data


def test_oversized_request_is_rejected(client):
    response = client.post('/login', data='x' * (129 * 1024),
                           content_type='application/x-www-form-urlencoded')
    assert response.status_code == 413
    assert b'A small pause.' in response.data


def test_notes_create_view_and_refresh_safety(app, client):
    register(client)
    text = 'A small idea\n\n  Keep my spacing.\n<script>alert(1)</script>'
    response = client.post('/', data={'csrf_token': token(client, '/'), 'note': text})
    assert response.status_code == 302
    page = client.get('/')
    assert b'A small idea' in page.data
    assert b'&lt;script&gt;' in page.data
    assert b'<script>alert(1)</script>' not in page.data
    client.get('/')
    with app.app_context():
        assert Note.query.one().data == text
        assert Note.query.one().user_id == User.query.one().id


@pytest.mark.parametrize('text', [None, '', ' \n\t ', 'a' * 10001])
def test_note_validation(app, client, text):
    register(client)
    data = {'csrf_token': token(client, '/')}
    if text is not None:
        data['note'] = text
    response = client.post('/', data=data)
    assert response.status_code == 200
    with app.app_context():
        assert Note.query.count() == 0


def test_maximum_note_and_display_of_older_larger_note(app, client):
    register(client)
    response = client.post('/', data={'csrf_token': token(client, '/'), 'note': 'x' * 10000})
    assert response.status_code == 302
    with app.app_context():
        db.session.add(Note(data='historical-' + 'y' * 11000, user_id=User.query.one().id))
        db.session.commit()
    assert b'historical-' in client.get('/').data


def add_note(client, text='A private thought'):
    response = client.post('/', data={'csrf_token': token(client, '/'), 'note': text})
    assert response.status_code == 302


def test_delete_own_note_and_empty_state(app, client):
    register(client)
    add_note(client)
    with app.app_context():
        note_id = Note.query.one().id
    response = client.post('/delete-note', json={'noteId': note_id},
                           headers={'X-CSRFToken': token(client, '/')})
    assert response.status_code == 200
    assert response.json == {}
    assert b'A fresh page. All yours.' in client.get('/').data
    with app.app_context():
        assert Note.query.count() == 0


def test_cross_user_notes_and_delete_protection(app, client):
    register(client, 'first@example.com')
    add_note(client, 'First user secret')
    with app.app_context():
        first_note = Note.query.one().id
        owner_id = Note.query.one().user_id
    logout(client)
    register(client, 'second@example.com', 'Second')
    assert b'First user secret' not in client.get('/').data
    assert b'First user secret' not in client.get('/?user_id=' + str(owner_id)).data
    client.post('/', data={'csrf_token': token(client, '/'), 'note': 'Second user note',
                           'user_id': owner_id, 'id': first_note})
    for note_id in (first_note, 999999):
        response = client.post('/delete-note', json={'noteId': note_id},
                               headers={'X-CSRFToken': token(client, '/')})
        assert response.status_code == 404
        assert response.json == {'error': 'This note could not be found.'}
    with app.app_context():
        assert db.session.get(Note, first_note).data == 'First user secret'
        assert Note.query.filter_by(data='Second user note').one().user_id != owner_id
        assert Note.query.count() == 2


@pytest.mark.parametrize('payload', [None, [], {}, {'noteId': None}, {'noteId': '1'}, {'noteId': True}, {'noteId': -1}, {'noteId': 1.5}, {'noteId': 2**64}])
def test_invalid_delete_requests(client, payload):
    register(client)
    response = client.post('/delete-note', json=payload, headers={'X-CSRFToken': token(client, '/')})
    assert response.status_code == 400
    assert response.is_json


def test_malformed_json_delete(client):
    register(client)
    response = client.post('/delete-note', data='{invalid', content_type='application/json',
                           headers={'X-CSRFToken': token(client, '/')})
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize('path', ['/login', '/sign-up', '/', '/logout', '/delete-note'])
@pytest.mark.parametrize('csrf_value', [None, 'invalid'])
def test_csrf_required_for_every_state_change(client, app, path, csrf_value):
    register(client)
    add_note(client)
    data = {'note': 'must not save', 'email': 'evil@example.com'}
    if csrf_value is not None:
        data['csrf_token'] = csrf_value
    response = client.post(path, data=data)
    assert response.status_code == 400
    assert client.get('/').status_code == 200
    with app.app_context():
        assert User.query.count() == 1
        assert Note.query.count() == 1


def test_csrf_token_cannot_be_reused_from_another_session(app, client):
    register(client)
    alien_token = token(app.test_client())
    response = client.post('/', data={'csrf_token': alien_token, 'note': 'forged'})
    assert response.status_code == 400


def test_error_pages_and_headers(client):
    response = client.get('/does-not-exist')
    assert response.status_code == 404
    assert b'A small pause.' in response.data
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert "script-src 'self'" in response.headers['Content-Security-Policy']
    assert client.get('/delete-note').status_code == 405


def test_database_failure_rolls_back(app, client, monkeypatch):
    register(client)
    csrf_token = token(client, '/')
    def fail():
        raise SQLAlchemyError('private database details')
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'commit', fail)
        response = client.post('/', data={'csrf_token': csrf_token, 'note': 'not saved'})
    assert response.status_code == 500
    assert b'could not save' in response.data
    assert b'private database details' not in response.data
    with app.app_context():
        assert Note.query.count() == 0


def test_factory_opens_original_schema_without_modifying_rows(tmp_path):
    path = tmp_path / 'existing.db'
    with sqlite3.connect(path) as conn:
        conn.executescript('''
            CREATE TABLE user (id INTEGER PRIMARY KEY, email VARCHAR(150) UNIQUE,
                               password VARCHAR(150), first_name VARCHAR(150));
            CREATE TABLE note (id INTEGER PRIMARY KEY, data VARCHAR(10000),
                               date DATETIME, user_id INTEGER REFERENCES user(id));
        ''')
        conn.execute('INSERT INTO user VALUES (1, ?, ?, ?)', ('legacy@example.com', LEGACY_HASH, 'Legacy'))
        conn.execute('INSERT INTO note VALUES (1, ?, ?, 1)', ('Original note\nUnchanged.', '2025-01-01 12:00:00'))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-key',
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + path.as_posix()})
    client = app.test_client()
    assert b'Original note' in login(client, 'legacy@example.com', 'legacy-password').data
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
