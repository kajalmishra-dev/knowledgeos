import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hasher.verify(password, hashed_password)


def create_access_token(*, user_id: UUID, email: str, secret: str, algorithm: str, minutes: int) -> tuple[str, int]:
    expires_in = minutes * 60
    expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token, expires_in


def decode_access_token(token: str, secret: str, algorithm: str) -> dict:
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
