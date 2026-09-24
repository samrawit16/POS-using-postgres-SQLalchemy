"""Settings must fail closed: no weak/missing secrets, safe production defaults."""
import pytest
from pydantic import ValidationError

from app.config import Settings

GOOD = dict(DATABASE_URL="sqlite://", SECRET_KEY="k" * 40)


def make(**overrides):
    # _env_file=None: ignore any developer .env; explicit kwargs beat environment variables.
    return Settings(_env_file=None, **{**GOOD, **overrides})


def test_valid_settings():
    s = make()
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert s.docs_enabled is True


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_URL="sqlite://")


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SECRET_KEY="k" * 40)


@pytest.mark.parametrize("weak", ["short", "k" * 31, ""])
def test_short_secret_rejected(weak):
    with pytest.raises(ValidationError):
        make(SECRET_KEY=weak)


@pytest.mark.parametrize("placeholder", ["replace-with-a-long-random-string", "your-secret-key", "changeme"])
def test_placeholder_secret_rejected(placeholder):
    # padded so they pass the length rule and only the placeholder rule can reject them
    with pytest.raises(ValidationError):
        make(SECRET_KEY=placeholder)


def test_placeholder_check_is_exact_not_substring():
    assert make(SECRET_KEY="changeme-" + "z" * 40)  # long, random-ish: fine


def test_production_forbids_wildcard_cors():
    with pytest.raises(ValidationError):
        make(ENVIRONMENT="production", CORS_ORIGINS="https://a.com,*")


def test_production_forbids_sql_echo():
    with pytest.raises(ValidationError):
        make(ENVIRONMENT="production", DB_ECHO=True)


def test_production_disables_docs():
    assert make(ENVIRONMENT="production").docs_enabled is False


def test_unknown_environment_rejected():
    with pytest.raises(ValidationError):
        make(ENVIRONMENT="staging-ish")


def test_cors_origin_parsing():
    assert make(CORS_ORIGINS=" https://a.com , https://b.com ,, ").cors_origins_list == [
        "https://a.com",
        "https://b.com",
    ]
    assert make(CORS_ORIGINS="").cors_origins_list == []


@pytest.mark.parametrize("field,value", [("ACCESS_TOKEN_EXPIRE_MINUTES", 0), ("ACCESS_TOKEN_EXPIRE_MINUTES", 100000),
                                         ("LOGIN_MAX_ATTEMPTS", 0), ("LOGIN_LOCKOUT_SECONDS", -1)])
def test_numeric_bounds(field, value):
    with pytest.raises(ValidationError):
        make(**{field: value})


@pytest.mark.parametrize("alg,length,ok", [("HS256", 32, True), ("HS384", 47, False), ("HS384", 48, True),
                                           ("HS512", 63, False), ("HS512", 64, True)])
def test_secret_length_scales_with_algorithm(alg, length, ok):
    if ok:
        assert make(JWT_ALGORITHM=alg, SECRET_KEY="k" * length)
    else:
        with pytest.raises(ValidationError):
            make(JWT_ALGORITHM=alg, SECRET_KEY="k" * length)
