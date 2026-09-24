"""Headers, CORS, production hardening, error hygiene, startup."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parent.parent


def run_app_snippet(code, tmp_path, **env):
    """Run code in a fresh interpreter with a controlled environment.

    cwd is an empty temp dir (not the repo) so a developer's real .env can never leak into the test.
    """
    base = {k: v for k, v in os.environ.items() if k not in {"ENVIRONMENT", "SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS", "DB_ECHO"}}
    base.update(PYTHONPATH=str(ROOT), DATABASE_URL="sqlite://", **env)
    return subprocess.run([sys.executable, "-c", code], env=base, cwd=tmp_path, capture_output=True, text=True, timeout=60)


# ---------------------------------------------------------------- headers
def test_security_headers_on_every_response(client, cashier):
    for r in (client.get("/health"), client.get("/products/"), client.get("/products/", headers=cashier.headers)):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["cache-control"] == "no-store"
        assert "strict-transport-security" not in r.headers  # HSTS only in production (would break local http)


def test_error_responses_also_carry_security_headers(client):
    r = client.get("/products/")  # 401
    assert r.status_code == 401 and r.headers["x-content-type-options"] == "nosniff"


def test_no_cors_headers_by_default(client):
    r = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    pre = client.options("/products/", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in pre.headers


# ---------------------------------------------------------------- error hygiene
def test_validation_errors_do_not_leak_internals(client, manager):
    r = client.post("/products/", json={"name": 5}, headers=manager.headers)
    assert r.status_code == 422
    assert "Traceback" not in r.text and "sqlalchemy" not in r.text.lower()


def test_unknown_route_is_plain_404(client):
    assert client.get("/nope").status_code == 404
    assert client.get("/.env").status_code == 404
    assert client.get("/../etc/passwd").status_code == 404


def test_wrong_method_is_405_after_auth(client):
    assert client.patch("/products/1").status_code in (401, 405)


def test_health_endpoint_is_public_and_minimal(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


# ---------------------------------------------------------------- production mode (fresh interpreter)
PROD_SNIPPET = '''
import json
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
allowed, denied = "https://pos.example.com", "https://evil.example"
pre = c.options("/products/", headers={"Origin": allowed, "Access-Control-Request-Method": "DELETE"})
print(json.dumps({
    "docs": c.get("/docs").status_code,
    "redoc": c.get("/redoc").status_code,
    "openapi": c.get("/openapi.json").status_code,
    "hsts": c.get("/health").headers.get("strict-transport-security"),
    "cors_allowed": c.get("/health", headers={"Origin": allowed}).headers.get("access-control-allow-origin"),
    "cors_denied": c.get("/health", headers={"Origin": denied}).headers.get("access-control-allow-origin"),
    "cors_credentials": c.get("/health", headers={"Origin": allowed}).headers.get("access-control-allow-credentials"),
    "preflight_methods": pre.headers.get("access-control-allow-methods"),
}))
'''


def test_production_mode_hardening(tmp_path):
    p = run_app_snippet(PROD_SNIPPET, tmp_path, ENVIRONMENT="production", SECRET_KEY="p" * 64,
                        CORS_ORIGINS="https://pos.example.com")
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    assert out["docs"] == out["redoc"] == out["openapi"] == 404  # API schema not advertised in production
    assert "max-age=" in out["hsts"]
    assert out["cors_allowed"] == "https://pos.example.com"
    assert out["cors_denied"] is None
    assert out["cors_credentials"] is None  # bearer tokens, not cookies
    assert "PATCH" not in out["preflight_methods"] and "DELETE" in out["preflight_methods"]


def test_docs_are_available_in_development(tmp_path):
    p = run_app_snippet(
        "from fastapi.testclient import TestClient\nfrom app.main import app\nprint(TestClient(app).get('/docs').status_code)",
        tmp_path, ENVIRONMENT="development", SECRET_KEY="d" * 64)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip().splitlines()[-1] == "200"


@pytest.mark.parametrize("env,why", [
    ({}, "no SECRET_KEY at all"),
    ({"SECRET_KEY": "tooshort"}, "short SECRET_KEY"),
    ({"SECRET_KEY": "changeme"}, "placeholder SECRET_KEY"),
    ({"SECRET_KEY": "p" * 64, "ENVIRONMENT": "production", "CORS_ORIGINS": "*"}, "wildcard CORS in production"),
])
def test_app_refuses_to_start_with_unsafe_config(tmp_path, env, why):
    p = run_app_snippet("import app.main", tmp_path, **env)
    assert p.returncode != 0, f"app started despite: {why}"
    assert "ValidationError" in p.stderr


def test_app_refuses_to_start_without_database_url(tmp_path):
    base = {k: v for k, v in os.environ.items() if k not in {"DATABASE_URL", "SECRET_KEY", "ENVIRONMENT"}}
    base.update(PYTHONPATH=str(ROOT), SECRET_KEY="s" * 64)
    p = subprocess.run([sys.executable, "-c", "import app.main"], env=base, cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode != 0 and "DATABASE_URL" in p.stderr


# ---------------------------------------------------------------- startup
def test_lifespan_creates_missing_tables(monkeypatch, engine, session_factory):
    from app import main
    from app.database import Base

    Base.metadata.drop_all(engine)
    assert not inspect(engine).has_table("users")

    monkeypatch.setattr(main, "engine", engine)  # the test DB, shared across threads
    with TestClient(main.app) as c:  # entering the context runs the lifespan
        assert c.get("/health").status_code == 200
    names = set(inspect(engine).get_table_names())
    assert {"users", "products", "sales", "sale_items", "payments", "receipts", "inventory",
            "customers", "suppliers", "categories"} <= names
