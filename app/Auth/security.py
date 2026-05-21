import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Request
from fastapi.responses import Response

SESSION_COOKIE = "habit_tracker_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7
PASSWORD_ITERATIONS = 310_000
SECRET_KEY = os.getenv("SECRET_KEY", "habit-tracker-dev-secret")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS
    )
    encoded_hash = base64.b64encode(password_hash).decode("ascii")
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${encoded_hash}"


def verify_password(password: str, stored_password: str) -> bool:
    if not stored_password.startswith("pbkdf2_sha256$"):
        return False

    try:
        algorithm, iterations, salt, expected_hash = stored_password.split("$", 3)
        iterations_count = int(iterations)
    except (ValueError, TypeError):
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations_count
    )
    encoded_hash = base64.b64encode(password_hash).decode("ascii")
    return secrets.compare_digest(encoded_hash, expected_hash)


def _sign_payload(payload: str) -> str:
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def create_session_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + SESSION_MAX_AGE
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{_sign_payload(encoded_payload)}"


def get_session_user_id(request: Request) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or "." not in token:
        return None

    encoded_payload, signature = token.rsplit(".", 1)
    if not secrets.compare_digest(_sign_payload(encoded_payload), signature):
        return None

    try:
        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None

    return payload.get("user_id")


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax"
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)
