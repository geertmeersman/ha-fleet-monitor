import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from werkzeug.security import generate_password_hash

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DB_PATH"] = _db_path

import db  # noqa: E402
from app import app as flask_app  # noqa: E402

TEST_PASSWORD = "testpassword"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_module_db():
    yield
    try:
        os.close(_db_fd)
        os.unlink(_db_path)
    except Exception:
        pass


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DB_PATH"] = db_path
    db.DB_PATH = db_path

    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.init_db()
        db.set_setting("password_hash", generate_password_hash(TEST_PASSWORD))
    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"password": TEST_PASSWORD}, follow_redirects=True)
    return client
