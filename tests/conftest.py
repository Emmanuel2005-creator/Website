import re

import pytest

from website import create_app, db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-only-key-never-used-outside-tests',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + (tmp_path / 'test.db').as_posix(),
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def token(client, path='/login'):
    page = client.get(path)
    match = re.search(rb'name="csrf-token" content="([^"]+)"', page.data)
    assert match, page.data
    return match.group(1).decode()


def register(client, email='alex@example.com', name='Alex', password='test-password'):
    return client.post('/sign-up', data={
        'csrf_token': token(client, '/sign-up'),
        'email': email, 'firstName': name, 'password1': password, 'password2': password,
    }, follow_redirects=True)


def login(client, email='alex@example.com', password='test-password'):
    return client.post('/login', data={
        'csrf_token': token(client), 'email': email, 'password': password,
    }, follow_redirects=True)


def logout(client):
    return client.post('/logout', data={'csrf_token': token(client, '/')})
