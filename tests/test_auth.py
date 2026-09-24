"""Login, tokens, lockout, password change."""
import time

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select

import app.login_throttle as throttle_mod
from app.models.user import User
from app.security import create_access_token, verify_password
from tests.conftest import STRONG_PASSWORD, do_login


# ---------------------------------------------------------------- login
def test_login_success_and_me(client, make_user):
    u = make_user("manager")
    r = do_login(client, u.username, u.password)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == u.username
    assert me.json()["role"] == "manager"
    assert "password" not in me.text and "password_hash" not in me.text and "argon2" not in me.text


def test_login_is_case_insensitive_on_username(client, make_user):
    u = make_user("cashier", username="alice")
    assert do_login(client, "ALICE", u.password).status_code == 200
    assert do_login(client, "  alice  ", u.password).status_code == 200


def test_wrong_password_and_unknown_user_look_identical(client, make_user):
    u = make_user()
    wrong_pw = do_login(client, u.username, "not-the-password-1")
    no_user = do_login(client, "nobody-here", "not-the-password-1")
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()  # no username enumeration
    assert wrong_pw.headers["www-authenticate"] == "Bearer"


def test_unknown_username_still_costs_a_password_hash_check(client, make_user, monkeypatch):
    """Anti-enumeration: an unknown username must burn the same work as a real one.

    (Asserting on wall-clock time would be flaky, so we assert the padding step runs.)
    """
    import app.services.auth as auth_service

    calls = []
    monkeypatch.setattr(auth_service, "burn_password_check", lambda pw: calls.append(pw))
    u = make_user()
    do_login(client, "no-such-user", "whatever-123")
    assert calls == ["whatever-123"]
    do_login(client, u.username, "wrong-password-1")
    do_login(client, u.username, u.password)
    assert len(calls) == 1  # real users go through real verification instead


def test_login_requires_both_fields(client):
    assert client.post("/auth/login", data={"username": "x"}).status_code == 422
    assert client.post("/auth/login", data={}).status_code == 422


def test_login_rejects_json_body(client, make_user):
    u = make_user()
    r = client.post("/auth/login", json={"username": u.username, "password": u.password})
    assert r.status_code == 422  # OAuth2 form only


@pytest.mark.parametrize("payload", ["' OR '1'='1", "admin'--", '" OR ""="', "'; DROP TABLE users;--"])
def test_sql_injection_in_login_fields_fails_safely(client, make_user, payload):
    make_user("admin", username="admin")
    assert do_login(client, payload, payload).status_code == 401
    assert do_login(client, "admin", payload).status_code == 401
    # table still intact
    assert do_login(client, "admin", STRONG_PASSWORD).status_code == 200


def test_disabled_account_cannot_log_in(client, make_user):
    u = make_user(is_active=False)
    r = do_login(client, u.username, u.password)
    assert r.status_code == 403
    # ...but a wrong password on a disabled account reveals nothing extra
    assert do_login(client, u.username, "wrong-password-1").status_code == 401


def test_legacy_plaintext_password_hash_cannot_log_in(client, session_factory):
    """Rows written by the old API stored the raw password in password_hash."""
    with session_factory() as db:
        db.add(User(username="legacy", email="l@x.co", password_hash="hunter2hunter2", first_name="L",
                    last_name="L", role="admin"))
        db.commit()
    assert do_login(client, "legacy", "hunter2hunter2").status_code == 401


def test_login_transparently_rehashes_weak_hashes(client, session_factory):
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(STRONG_PASSWORD)
    with session_factory() as db:
        db.add(User(username="oldhash", email="o@x.co", password_hash=weak, first_name="O", last_name="O",
                    role="cashier"))
        db.commit()
    assert do_login(client, "oldhash", STRONG_PASSWORD).status_code == 200
    with session_factory() as db:
        stored = db.scalars(select(User).where(User.username == "oldhash")).one().password_hash
    assert stored != weak and verify_password(STRONG_PASSWORD, stored)


# ---------------------------------------------------------------- token handling on protected routes
def test_no_token_is_401_with_bearer_challenge(client):
    r = client.get("/products/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer", "Bearer ", "Bearer not.a.jwt", "Basic dXNlcjpwYXNz", "token abc", "bearer"])
def test_malformed_authorization_headers(client, header):
    assert client.get("/products/", headers={"Authorization": header}).status_code == 401


def test_expired_token_is_401(client, make_user, session_factory):
    from datetime import timedelta

    u = make_user()
    with session_factory() as db:
        h = db.scalars(select(User).where(User.id == u.id)).one().password_hash
    token = create_access_token(u.id, h, expires_delta=timedelta(seconds=-1))
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_deleted_user_is_401(client, admin, make_user):
    victim = make_user("cashier")
    token = do_login(client, victim.username, victim.password).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.delete(f"/users/{victim.id}", headers=admin.headers).status_code == 204
    assert client.get("/auth/me", headers=h).status_code == 401


def test_deactivating_user_revokes_existing_token_immediately(client, admin, make_user):
    victim = make_user("cashier")
    token = do_login(client, victim.username, victim.password).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/products/", headers=h).status_code == 200
    assert client.put(f"/users/{victim.id}", json={"is_active": False}, headers=admin.headers).status_code == 200
    assert client.get("/products/", headers=h).status_code == 401


def test_role_change_takes_effect_immediately(client, admin, make_user):
    u = make_user("manager")
    h = {"Authorization": "Bearer " + do_login(client, u.username, u.password).json()["access_token"]}
    assert client.post("/categories/", json={"name": "A"}, headers=h).status_code == 201
    client.put(f"/users/{u.id}", json={"role": "cashier"}, headers=admin.headers)
    assert client.post("/categories/", json={"name": "B"}, headers=h).status_code == 403


# ---------------------------------------------------------------- brute force lockout
def test_lockout_after_max_failures(client, make_user):
    u = make_user()
    for _ in range(5):
        assert do_login(client, u.username, "wrong-password-1").status_code == 401
    locked = do_login(client, u.username, "wrong-password-1")
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0
    # even the CORRECT password is refused while locked out
    assert do_login(client, u.username, u.password).status_code == 429


def test_lockout_is_per_username(client, make_user):
    a, b = make_user(username="aaa"), make_user(username="bbb")
    for _ in range(5):
        do_login(client, a.username, "wrong-password-1")
    assert do_login(client, a.username, a.password).status_code == 429
    assert do_login(client, b.username, b.password).status_code == 200


def test_lockout_applies_to_nonexistent_usernames_too(client):
    for _ in range(5):
        do_login(client, "ghost", "wrong-password-1")
    assert do_login(client, "ghost", "wrong-password-1").status_code == 429  # can't probe by timing out early


def test_successful_login_resets_failure_counter(client, make_user):
    u = make_user()
    for _ in range(4):
        do_login(client, u.username, "wrong-password-1")
    assert do_login(client, u.username, u.password).status_code == 200
    for _ in range(4):
        assert do_login(client, u.username, "wrong-password-1").status_code == 401  # not 429: counter was reset


def test_lockout_expires(client, make_user, monkeypatch):
    u = make_user()
    for _ in range(5):
        do_login(client, u.username, "wrong-password-1")
    assert do_login(client, u.username, u.password).status_code == 429
    real = time.monotonic()
    monkeypatch.setattr(throttle_mod.time, "monotonic", lambda: real + 301)
    assert do_login(client, u.username, u.password).status_code == 200


# ---------------------------------------------------------------- change password
def test_change_password_flow(client, make_user):
    u = make_user("cashier")
    token = do_login(client, u.username, u.password).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    new_pw = "An0therStrongPass!"

    r = client.post("/auth/change-password", json={"current_password": u.password, "new_password": new_pw}, headers=h)
    assert r.status_code == 204

    assert do_login(client, u.username, u.password).status_code == 401  # old password dead
    assert do_login(client, u.username, new_pw).status_code == 200      # new one works
    assert client.get("/auth/me", headers=h).status_code == 401         # tokens issued before the change are revoked


def test_change_password_needs_correct_current_password(client, cashier):
    r = client.post("/auth/change-password",
                    json={"current_password": "totally-wrong-1", "new_password": "An0therStrongPass!"},
                    headers=cashier.headers)
    assert r.status_code == 400


def test_change_password_rejects_same_and_weak(client, cashier):
    same = client.post("/auth/change-password",
                       json={"current_password": cashier.user.password, "new_password": cashier.user.password},
                       headers=cashier.headers)
    assert same.status_code == 400
    weak = client.post("/auth/change-password",
                       json={"current_password": cashier.user.password, "new_password": "short1"},
                       headers=cashier.headers)
    assert weak.status_code == 422


def test_change_password_requires_auth(client):
    r = client.post("/auth/change-password", json={"current_password": "x", "new_password": "y"})
    assert r.status_code == 401
