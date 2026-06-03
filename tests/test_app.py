import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, init_db

init_db()


def test_login_page():
    client = app.test_client()
    response = client.get('/login')
    assert response.status_code == 200


def test_signup_page():
    client = app.test_client()
    response = client.get('/signup')
    assert response.status_code == 200


def test_forgot_password_page():
    client = app.test_client()
    response = client.get('/forgot-password')
    assert response.status_code == 200


def test_index_redirect():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 302


def test_logout_redirect():
    client = app.test_client()
    response = client.get('/logout')
    assert response.status_code == 302


def test_invalid_reset_token():
    client = app.test_client()
    response = client.get('/reset-password/fake_token')
    assert response.status_code == 302


def test_signup_post():
    client = app.test_client()

    response = client.post(
        '/signup',
        data={
            'email': 'ci_test_user_unique@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '123456'
        }
    )

    assert response.status_code == 302
