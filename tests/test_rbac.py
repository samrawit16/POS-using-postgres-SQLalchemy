"""Authorization matrix: who may call what.

For every endpoint we check three things:
  * anonymous            -> 401
  * a role that is NOT allowed -> 403 (and nothing gets created/changed)
  * a role that IS allowed     -> anything except 401/403 (404/422/... is fine: it got past the guard)
"""
import pytest

from app.main import app

ALL = {"admin", "manager", "cashier"}
MGR = {"admin", "manager"}
ADMIN = {"admin"}

# (method, path, roles allowed)
MATRIX = [
    ("GET", "/categories/", ALL), ("GET", "/categories/1", ALL),
    ("POST", "/categories/", MGR), ("PUT", "/categories/1", MGR), ("DELETE", "/categories/1", MGR),

    ("GET", "/suppliers/", MGR), ("GET", "/suppliers/1", MGR),
    ("POST", "/suppliers/", MGR), ("PUT", "/suppliers/1", MGR), ("DELETE", "/suppliers/1", MGR),

    ("GET", "/products/", ALL), ("GET", "/products/1", ALL),
    ("POST", "/products/", MGR), ("PUT", "/products/1", MGR), ("DELETE", "/products/1", MGR),

    ("GET", "/inventory/", ALL), ("GET", "/inventory/1", ALL),
    ("POST", "/inventory/", MGR), ("PUT", "/inventory/1", MGR), ("DELETE", "/inventory/1", MGR),

    ("GET", "/customers/", ALL), ("GET", "/customers/1", ALL),
    ("POST", "/customers/", ALL), ("PUT", "/customers/1", ALL), ("DELETE", "/customers/1", MGR),

    ("GET", "/users/", ADMIN), ("GET", "/users/1", ADMIN),
    ("POST", "/users/", ADMIN), ("PUT", "/users/1", ADMIN), ("DELETE", "/users/1", ADMIN),

    ("GET", "/sales/", ALL), ("GET", "/sales/1", ALL),
    ("POST", "/sales/", ALL), ("PUT", "/sales/1", MGR), ("DELETE", "/sales/1", MGR),

    ("GET", "/sale-items/", ALL), ("GET", "/sale-items/1", ALL),
    ("POST", "/sale-items/", ALL), ("PUT", "/sale-items/1", MGR), ("DELETE", "/sale-items/1", MGR),

    ("GET", "/payments/", ALL), ("GET", "/payments/1", ALL),
    ("POST", "/payments/", ALL), ("PUT", "/payments/1", MGR), ("DELETE", "/payments/1", MGR),

    ("GET", "/receipts/", ALL), ("GET", "/receipts/1", ALL),
    ("POST", "/receipts/", ALL), ("PUT", "/receipts/1", MGR), ("DELETE", "/receipts/1", MGR),

    ("GET", "/auth/me", ALL),
    ("POST", "/auth/change-password", ALL),
]
IDS = [f"{m} {p}" for m, p, _ in MATRIX]


def call(client, method, path, headers=None):
    kwargs = {"headers": headers or {}}
    if method in ("POST", "PUT"):
        kwargs["json"] = {}  # invalid body on purpose: guards must fire before validation
    return client.request(method, path, **kwargs)


@pytest.fixture()
def people(login_as):
    # created in this order so admin gets id=1 (matters for DELETE /users/1 below)
    return {"admin": login_as("admin"), "manager": login_as("manager"), "cashier": login_as("cashier")}


@pytest.mark.parametrize("method,path,allowed", MATRIX, ids=IDS)
def test_anonymous_gets_401(client, method, path, allowed):
    assert call(client, method, path).status_code == 401


@pytest.mark.parametrize("method,path,allowed", MATRIX, ids=IDS)
def test_role_matrix(client, people, method, path, allowed):
    for role, who in people.items():
        status = call(client, method, path, who.headers).status_code
        if role in allowed:
            assert status not in (401, 403), f"{role} should be allowed on {method} {path}, got {status}"
        else:
            assert status == 403, f"{role} should be forbidden on {method} {path}, got {status}"


PUBLIC = {("POST", "/auth/login")}


def _all_operations():
    """(METHOD, concrete path) for every operation the app documents in its OpenAPI schema."""
    import re

    ops = set()
    for path, item in app.openapi()["paths"].items():
        concrete = re.sub(r"\{[^}]+\}", "1", path)
        for method in item:
            ops.add((method.upper(), concrete))
    return ops


def test_every_endpoint_requires_authentication(client):
    """Default-deny: a new endpoint added without a guard makes this fail."""
    ops = _all_operations() - PUBLIC
    assert len(ops) >= 50  # sanity: we really did walk the whole API
    unprotected = [(m, p) for m, p in sorted(ops) if call(client, m, p).status_code != 401]
    assert not unprotected, f"endpoints reachable without a token: {unprotected}"


def test_permission_matrix_covers_every_endpoint():
    """Adding an endpoint forces a decision about which roles may call it."""
    documented = _all_operations() - PUBLIC
    in_matrix = {(m, p) for m, p, _ in MATRIX}
    assert documented == in_matrix, (
        f"missing from MATRIX: {sorted(documented - in_matrix)}; stale in MATRIX: {sorted(in_matrix - documented)}"
    )
