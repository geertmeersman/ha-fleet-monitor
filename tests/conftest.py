import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_PASSWORD", "testpassword")

import db
from app import app as flask_app


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DB_PATH"] = db_path
    db.DB_PATH = db_path

    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.init_db()
    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"password": "testpassword"})
    return client
