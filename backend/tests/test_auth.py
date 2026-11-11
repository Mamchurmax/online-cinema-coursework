from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import Settings
from app.core.security import create_access_token
from app.models import User, UserRole

PASSWORD = "s3cret-pass"


def register(client: TestClient, email: str = "viewer@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Viewer"},
    )


def login(client: TestClient, email: str = "viewer@example.com", password: str = PASSWORD):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user_with_hashed_password(client: TestClient, session: Session) -> None:
    response = register(client, "Viewer@Example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "viewer@example.com"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body

    stored = session.get(User, body["id"])
    assert stored is not None
    assert stored.password_hash != PASSWORD


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    register(client)

    response = register(client, "VIEWER@example.com")

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD, "display_name": "X"},
        {"email": "a@example.com", "password": "short", "display_name": "X"},
        {"email": "a@example.com", "password": PASSWORD, "display_name": ""},
    ],
)
def test_register_validates_input(client: TestClient, payload: dict) -> None:
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422


def test_login_returns_token_for_me_endpoint(client: TestClient) -> None:
    register(client)

    response = login(client, "VIEWER@example.com")

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    me = client.get("/api/v1/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["email"] == "viewer@example.com"


@pytest.mark.parametrize(
    ("email", "password"),
    [("viewer@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)],
)
def test_login_rejects_bad_credentials(client: TestClient, email: str, password: str) -> None:
    register(client)

    assert login(client, email, password).status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/me").status_code == 401


def test_me_rejects_tampered_and_expired_tokens(client: TestClient) -> None:
    user_id = register(client).json()["id"]
    settings = Settings.instance()

    forged = create_access_token(user_id, UserRole.USER, settings) + "x"
    expired = jwt.encode(
        {"sub": str(user_id), "role": "user", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    for token in (forged, expired, "garbage"):
        assert client.get("/api/v1/me", headers=auth_header(token)).status_code == 401


def test_me_rejects_token_of_deleted_user(client: TestClient) -> None:
    token = create_access_token(999, UserRole.USER, Settings.instance())

    assert client.get("/api/v1/me", headers=auth_header(token)).status_code == 401


def test_require_admin_allows_only_admins() -> None:
    admin = User(email="a@example.com", password_hash="x", display_name="A", role=UserRole.ADMIN)
    viewer = User(email="v@example.com", password_hash="x", display_name="V", role=UserRole.USER)

    assert require_admin(admin) is admin
    with pytest.raises(HTTPException) as exc_info:
        require_admin(viewer)
    assert exc_info.value.status_code == 403
