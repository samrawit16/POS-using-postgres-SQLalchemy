"""Test fixtures.

By default tests run on in-memory SQLite (fast, zero setup). To run them against
real PostgreSQL:

    TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/pos_test pytest

Every test starts from freshly created (empty) tables, so the target database
MUST be disposable - the name has to contain "test" or the run is aborted, which
stops you from ever pointing this at your real POS database.
"""
import itertools
import os
from types import SimpleNamespace

# --- environment must be set BEFORE the app is imported ---------------------------------
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "unit-test-secret-key-" + "k" * 60
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"
os.environ["LOGIN_LOCKOUT_SECONDS"] = "300"
os.environ["CORS_ORIGINS"] = ""
os.environ["DB_ECHO"] = "false"

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
if not TEST_DB_URL.startswith("sqlite"):
    from sqlalchemy.engine import make_url

    _dbname = (make_url(TEST_DB_URL).database or "").lower()
    if "test" not in _dbname:
        raise RuntimeError(
            f"Refusing to run: TEST_DATABASE_URL database '{_dbname}' must contain 'test' "
            "(the suite drops and recreates all tables)."
        )
os.environ["DATABASE_URL"] = TEST_DB_URL

import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models, security  # noqa: E402,F401
from app.database import Base, get_db  # noqa: E402
from app.login_throttle import login_throttle  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security import hash_password  # noqa: E402

STRONG_PASSWORD = "Str0ngPassw0rd!"


@pytest.fixture(autouse=True, scope="session")
def _fast_hasher():
    """Cheaper Argon2 parameters keep the suite quick; production keeps the library defaults."""
    original = security._hasher
    security._hasher = PasswordHasher(time_cost=2, memory_cost=64, parallelism=1)
    yield
    security._hasher = original


@pytest.fixture(scope="session")
def engine():
    if TEST_DB_URL.startswith("sqlite"):
        eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    login_throttle.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    login_throttle.clear()


@pytest.fixture()
def make_user(session_factory):
    """Insert a user straight into the DB (bypassing the API)."""
    counter = itertools.count(1)

    def _make(role="cashier", password=STRONG_PASSWORD, is_active=True, username=None, email=None):
        n = next(counter)
        username = username or f"{role}{n}"
        with session_factory() as db:
            user = User(
                username=username,
                email=email or f"{username}@example.com",
                password_hash=hash_password(password),
                first_name="Test",
                last_name=role.title(),
                role=role,
                is_active=is_active,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return SimpleNamespace(id=user.id, username=user.username, password=password, role=role)

    return _make


def do_login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture()
def login_as(client, make_user):
    """Create a user with the given role, log in, and return .user + ready-to-use .headers."""

    def _login(role="cashier", **kwargs):
        user = make_user(role, **kwargs)
        resp = do_login(client, user.username, user.password)
        assert resp.status_code == 200, resp.text
        return SimpleNamespace(
            user=user, headers={"Authorization": f"Bearer {resp.json()['access_token']}"}
        )

    return _login


@pytest.fixture()
def admin(login_as):
    return login_as("admin")


@pytest.fixture()
def manager(login_as):
    return login_as("manager")


@pytest.fixture()
def cashier(login_as):
    return login_as("cashier")
