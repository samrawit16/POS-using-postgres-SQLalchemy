"""Unit tests for password hashing and JWT handling (no HTTP involved)."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from argon2 import PasswordHasher

from app import security
from app.config import get_settings

SETTINGS = get_settings()


# ---------------------------------------------------------------- passwords
def test_hash_is_argon2id_and_not_plaintext():
    h = security.hash_password("correct horse 42")
    assert h.startswith("$argon2id$")
    assert "correct horse" not in h


def test_hashes_are_salted():
    assert security.hash_password("same-password-1") != security.hash_password("same-password-1")


def test_verify_password_roundtrip():
    h = security.hash_password("correct horse 42")
    assert security.verify_password("correct horse 42", h) is True
    assert security.verify_password("wrong horse 42", h) is False
    assert security.verify_password("", h) is False


@pytest.mark.parametrize("garbage", ["", "plaintext-password", "$2b$12$notreallybcrypt", "x" * 500])
def test_verify_password_never_raises_on_bad_stored_hash(garbage):
    # e.g. legacy rows where a plaintext password was stored in password_hash
    assert security.verify_password("anything", garbage) is False


def test_verify_handles_unicode_and_long_passwords():
    pw = "pässwörd-日本語-" + "x" * 120
    assert security.verify_password(pw, security.hash_password(pw))


def test_needs_rehash_detects_weaker_parameters():
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("pw-12345678ab")
    assert security.needs_rehash(weak) is True
    assert security.needs_rehash(security.hash_password("pw-12345678ab")) is False
    assert security.needs_rehash("not-a-hash") is False


# ---------------------------------------------------------------- JWT
PWHASH = "dummy-hash-value"


def test_token_roundtrip():
    token = security.create_access_token(42, PWHASH)
    user_id, fp = security.decode_access_token(token)
    assert user_id == 42
    assert security.fingerprint_matches(fp, PWHASH)
    assert not security.fingerprint_matches(fp, "some-other-hash")


def test_token_does_not_contain_password_hash():
    token = security.create_access_token(1, "SUPER-SECRET-HASH-VALUE")
    payload = jwt.decode(token, options={"verify_signature": False})
    assert "SUPER-SECRET-HASH-VALUE" not in str(payload)
    assert set(payload) == {"sub", "iat", "exp", "type", "pwd"}


def test_expired_token_rejected():
    token = security.create_access_token(1, PWHASH, expires_delta=timedelta(seconds=-5))
    assert security.decode_access_token(token) is None


def test_token_signed_with_other_key_rejected():
    forged = jwt.encode(
        {"sub": "1", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
         "type": "access", "pwd": "x"},
        "a-completely-different-secret-key-0123456789",
        algorithm="HS256",
    )
    assert security.decode_access_token(forged) is None


def test_tampered_payload_rejected():
    token = security.create_access_token(1, PWHASH)
    header, payload, sig = token.split(".")
    other = security.create_access_token(2, PWHASH).split(".")[1]
    assert security.decode_access_token(f"{header}.{other}.{sig}") is None


def test_alg_none_token_rejected():
    unsigned = jwt.encode(
        {"sub": "1", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
         "type": "access", "pwd": "x"},
        key=None,
        algorithm="none",
    )
    assert security.decode_access_token(unsigned) is None


def test_wrong_algorithm_token_rejected():
    payload = {"sub": "1", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
               "type": "access", "pwd": "x"}
    hs512 = jwt.encode(payload, SETTINGS.SECRET_KEY, algorithm="HS512")
    assert security.decode_access_token(hs512) is None  # only the configured alg is accepted


@pytest.mark.parametrize("missing", ["exp", "sub", "iat", "pwd"])
def test_token_missing_required_claim_rejected(missing):
    payload = {"sub": "1", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
               "type": "access", "pwd": "x"}
    payload.pop(missing)
    token = jwt.encode(payload, SETTINGS.SECRET_KEY, algorithm=SETTINGS.JWT_ALGORITHM)
    assert security.decode_access_token(token) is None


def test_non_access_token_type_rejected():
    payload = {"sub": "1", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
               "type": "refresh", "pwd": "x"}
    token = jwt.encode(payload, SETTINGS.SECRET_KEY, algorithm=SETTINGS.JWT_ALGORITHM)
    assert security.decode_access_token(token) is None


def test_non_numeric_subject_rejected():
    payload = {"sub": "admin' OR 1=1", "iat": datetime.now(timezone.utc),
               "exp": datetime.now(timezone.utc) + timedelta(hours=1), "type": "access", "pwd": "x"}
    token = jwt.encode(payload, SETTINGS.SECRET_KEY, algorithm=SETTINGS.JWT_ALGORITHM)
    assert security.decode_access_token(token) is None


@pytest.mark.parametrize("junk", ["", "abc", "a.b.c", "Bearer x", "\x00", "." * 10])
def test_garbage_tokens_rejected(junk):
    assert security.decode_access_token(junk) is None
