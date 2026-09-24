"""User management (admin only): password handling, validation, last-admin protection."""
import pytest
from sqlalchemy import select

from app.models.user import User
from tests.conftest import STRONG_PASSWORD, do_login


def new_user(**overrides):
    body = dict(username="newbie", email="newbie@example.com", password=STRONG_PASSWORD,
                first_name="New", last_name="Bie", role="cashier")
    body.update(overrides)
    return body


def stored(session_factory, user_id):
    with session_factory() as db:
        return db.get(User, user_id)


# ---------------------------------------------------------------- create
def test_create_user_hashes_password_and_never_returns_it(client, admin, session_factory):
    r = client.post("/users/", json=new_user(), headers=admin.headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "newbie" and body["role"] == "cashier" and body["is_active"] is True
    for leaked in ("password", "password_hash", STRONG_PASSWORD, "argon2"):
        assert leaked not in r.text

    row = stored(session_factory, body["id"])
    assert row.password_hash.startswith("$argon2id$")
    assert STRONG_PASSWORD not in row.password_hash

    # and the new user can really log in
    assert do_login(client, "newbie", STRONG_PASSWORD).status_code == 200


def test_client_cannot_supply_a_pre_hashed_password(client, admin):
    """The old API accepted `password_hash` straight from the client. That field is gone."""
    body = new_user()
    del body["password"]
    body["password_hash"] = "$argon2id$v=19$m=65536,t=3,p=4$abc$def"
    assert client.post("/users/", json=body, headers=admin.headers).status_code == 422


def test_username_and_email_are_normalised(client, admin):
    r = client.post("/users/", json=new_user(username="  MiXeD.Case ", email="MiXeD@Example.COM"), headers=admin.headers)
    assert r.status_code == 201
    assert r.json()["username"] == "mixed.case" and r.json()["email"] == "mixed@example.com"


def test_duplicate_username_or_email_is_409_case_insensitive(client, admin):
    assert client.post("/users/", json=new_user(), headers=admin.headers).status_code == 201
    dup_name = client.post("/users/", json=new_user(username="NEWBIE", email="other@example.com"), headers=admin.headers)
    dup_mail = client.post("/users/", json=new_user(username="other", email="NEWBIE@example.com"), headers=admin.headers)
    assert dup_name.status_code == 409 and "Username" in dup_name.json()["detail"]
    assert dup_mail.status_code == 409 and "Email" in dup_mail.json()["detail"]


@pytest.mark.parametrize("password", [
    "short1A", "a" * 10 + "1", "onlyletterslongenough", "123456789012345", "  " * 8, "x1" * 65,
])
def test_weak_or_oversized_passwords_rejected(client, admin, password):
    assert client.post("/users/", json=new_user(password=password), headers=admin.headers).status_code == 422


@pytest.mark.parametrize("field,value", [
    ("role", "superuser"), ("role", "ADMIN "), ("role", ""),
    ("email", "not-an-email"), ("email", "a@b"), ("email", "x" * 250 + "@a.com"),
    ("username", "ab"), ("username", "has space"), ("username", "semi;colon"), ("username", "<script>"),
    ("first_name", ""), ("first_name", "x" * 101), ("phone", "1" * 21),
])
def test_invalid_user_fields_rejected(client, admin, field, value):
    assert client.post("/users/", json=new_user(**{field: value}), headers=admin.headers).status_code == 422


def test_password_never_appears_in_validation_error_echo(client, admin):
    r = client.post("/users/", json=new_user(password="tooshort1"), headers=admin.headers)
    assert r.status_code == 422
    # FastAPI echoes "input"; make sure it is at least not repeated in the error message text
    assert all("tooshort1" not in e["msg"] for e in r.json()["detail"])


# ---------------------------------------------------------------- read / list
def test_list_and_get_never_expose_hashes(client, admin, make_user):
    make_user("cashier")
    for r in (client.get("/users/", headers=admin.headers), client.get(f"/users/{admin.user.id}", headers=admin.headers)):
        assert r.status_code == 200
        assert "password" not in r.text and "argon2" not in r.text


def test_pagination(client, admin, make_user):
    for _ in range(5):
        make_user("cashier")
    everyone = client.get("/users/?limit=500", headers=admin.headers).json()
    assert len(everyone) == 6
    assert [u["id"] for u in everyone] == sorted(u["id"] for u in everyone)  # stable order
    page = client.get("/users/?skip=2&limit=3", headers=admin.headers).json()
    assert [u["id"] for u in page] == [u["id"] for u in everyone[2:5]]


@pytest.mark.parametrize("qs", ["limit=0", "limit=501", "limit=-1", "skip=-1", "limit=abc", f"skip={2**40}"])
def test_bad_pagination_rejected(client, admin, qs):
    assert client.get(f"/users/?{qs}", headers=admin.headers).status_code == 422


@pytest.mark.parametrize("uid", ["0", "-1", str(2**31), str(2**40), "abc"])
def test_bad_ids_are_422_not_500(client, admin, uid):
    assert client.get(f"/users/{uid}", headers=admin.headers).status_code == 422


def test_missing_user_is_404(client, admin):
    assert client.get("/users/99999", headers=admin.headers).status_code == 404
    assert client.put("/users/99999", json={"first_name": "x"}, headers=admin.headers).status_code == 404
    assert client.delete("/users/99999", headers=admin.headers).status_code == 404


# ---------------------------------------------------------------- update
def test_admin_can_reset_password_and_old_tokens_die(client, admin, make_user):
    victim = make_user("cashier")
    old_token = do_login(client, victim.username, victim.password).json()["access_token"]
    r = client.put(f"/users/{victim.id}", json={"password": "Br4ndNewPassword!"}, headers=admin.headers)
    assert r.status_code == 200 and "password" not in r.text
    assert do_login(client, victim.username, victim.password).status_code == 401
    assert do_login(client, victim.username, "Br4ndNewPassword!").status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_update_password_is_hashed_in_db(client, admin, make_user, session_factory):
    u = make_user()
    client.put(f"/users/{u.id}", json={"password": "Br4ndNewPassword!"}, headers=admin.headers)
    h = stored(session_factory, u.id).password_hash
    assert h.startswith("$argon2id$") and "Br4ndNewPassword" not in h


def test_partial_update_keeps_other_fields(client, admin, make_user):
    u = make_user("cashier")
    r = client.put(f"/users/{u.id}", json={"first_name": "Renamed"}, headers=admin.headers)
    assert r.status_code == 200 and r.json()["first_name"] == "Renamed" and r.json()["role"] == "cashier"
    assert do_login(client, u.username, u.password).status_code == 200  # password untouched


def test_update_rejects_explicit_null_on_required_fields(client, admin, make_user):
    u = make_user()
    for field in ("first_name", "email", "role", "username", "is_active", "password"):
        r = client.put(f"/users/{u.id}", json={field: None}, headers=admin.headers)
        assert r.status_code == 422, field
    assert client.put(f"/users/{u.id}", json={"phone": None}, headers=admin.headers).status_code == 200  # nullable


def test_update_uniqueness_ignores_self_but_catches_others(client, admin, make_user):
    a, b = make_user(username="aaa"), make_user(username="bbb")
    assert client.put(f"/users/{a.id}", json={"username": "AAA", "email": "aaa@example.com"}, headers=admin.headers).status_code == 200
    assert client.put(f"/users/{a.id}", json={"username": "bbb"}, headers=admin.headers).status_code == 409


def test_update_cannot_smuggle_password_hash(client, admin, make_user, session_factory):
    u = make_user()
    before = stored(session_factory, u.id).password_hash
    client.put(f"/users/{u.id}", json={"password_hash": "evil", "first_name": "X"}, headers=admin.headers)
    assert stored(session_factory, u.id).password_hash == before


# ---------------------------------------------------------------- last-admin protection
def test_cannot_delete_demote_or_deactivate_last_admin(client, admin):
    me = admin.user.id
    assert client.delete(f"/users/{me}", headers=admin.headers).status_code == 400
    assert client.put(f"/users/{me}", json={"role": "manager"}, headers=admin.headers).status_code == 400
    assert client.put(f"/users/{me}", json={"is_active": False}, headers=admin.headers).status_code == 400
    assert client.get("/auth/me", headers=admin.headers).status_code == 200  # still an admin


def test_admin_changes_allowed_when_another_active_admin_exists(client, admin, make_user):
    other = make_user("admin")
    assert client.put(f"/users/{other.id}", json={"role": "manager"}, headers=admin.headers).status_code == 200
    # back to a single admin -> protected again
    assert client.put(f"/users/{admin.user.id}", json={"role": "cashier"}, headers=admin.headers).status_code == 400


def test_inactive_admin_does_not_count_as_a_spare(client, admin, make_user):
    make_user("admin", is_active=False)
    assert client.delete(f"/users/{admin.user.id}", headers=admin.headers).status_code == 400


def test_updating_admin_without_losing_admin_status_is_fine(client, admin):
    r = client.put(f"/users/{admin.user.id}", json={"first_name": "Boss", "role": "admin"}, headers=admin.headers)
    assert r.status_code == 200


def test_delete_user_removes_row(client, admin, make_user, session_factory):
    u = make_user()
    assert client.delete(f"/users/{u.id}", headers=admin.headers).status_code == 204
    assert stored(session_factory, u.id) is None


def test_cannot_delete_user_who_has_sales(client, admin, cashier):
    assert client.post("/sales/", json={"user_id": cashier.user.id}, headers=cashier.headers).status_code == 201
    r = client.delete(f"/users/{cashier.user.id}", headers=admin.headers)
    assert r.status_code == 409  # FK violation is a clean 409, not a 500
    assert "foreign key" not in r.text.lower() and "sqlalchemy" not in r.text.lower()
