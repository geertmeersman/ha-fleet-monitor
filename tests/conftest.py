import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_PASSWORD", "testpassword")
os.environ.setdefault("DB_PATH", ":memory:")

from app import app as flask_app
from db import init_db


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        init_db()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"password": "testpassword"})
    return client
