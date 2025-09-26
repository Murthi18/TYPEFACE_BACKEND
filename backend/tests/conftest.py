# backend/tests/conftest.py
import os
import sys
import types
import mongomock
import pytest
from pathlib import Path

# Ensure the backend folder is on sys.path no matter where pytest is invoked from
BACKEND_DIR = Path(__file__).resolve().parents[1]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB", "typeface_test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

@pytest.fixture(scope="session")
def mock_db():
    mm_client = mongomock.MongoClient()
    mdb = mm_client["typeface_test"]
    users = mdb["users"]
    transactions = mdb["transactions"]
    users.create_index("email", unique=True)
    transactions.create_index([("user_id", 1), ("date", -1)])
    transactions.create_index([("user_id", 1), ("category", 1)])
    transactions.create_index([("user_id", 1), ("description", 1)])
    return types.SimpleNamespace(db=mdb, users=users, transactions=transactions)

@pytest.fixture(scope="session")
def app(mock_db):
    # Now this import will work whether you run `pytest` in repo root or in backend/
    from app import create_app
    import db as real_db

    real_db.users = mock_db.users
    real_db.transactions = mock_db.transactions
    real_db.db = mock_db.db

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app

@pytest.fixture()
def client(app):
    return app.test_client()
