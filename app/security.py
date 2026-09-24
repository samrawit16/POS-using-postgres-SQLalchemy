"""Password hashing (Argon2id) and JWT access tokens."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()  # argon2id with the library's current safe defaults

# A real hash of a random string, used to burn the same CPU time when the
# username doesn't exist, so response time doesn't reveal valid usernames.
_DUMMY_HASH = _hasher.hash("not-a-real-password-just-timing-padding")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def burn_password_check(password: str) -> None:
    """Spend the same time as a real verification (for unknown usernames)."""
    verify_password(password, _DUMMY_HASH)


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def password_fingerprint(password_hash: str) -> str:
    """Short, non-reversible tag of the current password hash (goes in the JWT)."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def fingerprint_matches(token_fp: str, password_hash: str) -> bool:
    return hmac.compare_digest(token_fp, password_fingerprint(password_hash))


def create_access_token(
    user_id: int, password_hash: str, expires_delta: timedelta | None = None
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "type": "access",
        "pwd": password_fingerprint(password_hash),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> tuple[int, str] | None:
    """Return (user_id, password_fingerprint) if the token is valid, else None."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # pinned: never trust the token's own "alg"
            options={"require": ["exp", "sub", "iat", "pwd"]},
        )
        if payload.get("type") != "access":
            return None
        return int(payload["sub"]), str(payload["pwd"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
