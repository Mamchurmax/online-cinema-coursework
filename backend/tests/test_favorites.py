"""Favorites API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Genre, Title, TitleType


@pytest.fixture
def titles(session: Session) -> list[Title]:
    items = [
        Title(type=TitleType.MOVIE, title="Сінтел", genres=[Genre(name="Фентезі")]),
        Title(type=TitleType.SERIES, title="Серіал"),
        Title(type=TitleType.MOVIE, title="Матриця"),
    ]
    session.add_all(items)
    session.commit()
    return items


def login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "fav-pass-123", "display_name": "F"})  # fmt: skip
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "fav-pass-123"}
                        ).json()["access_token"]  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


def test_add_list_and_remove_favorites(client: TestClient, titles: list[Title]) -> None:
    headers = login(client, "fan@example.com")
    sintel, series, _ = titles

    assert client.put(f"/api/v1/me/favorites/{sintel.id}", headers=headers).status_code == 204
    client.put(f"/api/v1/me/favorites/{series.id}", headers=headers)
    client.put(f"/api/v1/me/favorites/{sintel.id}", headers=headers)  # twice: still one entry

    favorites = client.get("/api/v1/me/favorites", headers=headers).json()
    assert {t["title"] for t in favorites} == {"Сінтел", "Серіал"}
    assert len(favorites) == 2
    sintel_item = next(t for t in favorites if t["title"] == "Сінтел")
    assert sintel_item["genres"] == [{"id": sintel.genres[0].id, "name": "Фентезі"}]
    assert sorted(client.get("/api/v1/me/favorites/ids", headers=headers).json()) == sorted(
        [sintel.id, series.id]
    )

    assert client.delete(f"/api/v1/me/favorites/{sintel.id}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/me/favorites/{sintel.id}", headers=headers).status_code == 204
    assert client.get("/api/v1/me/favorites/ids", headers=headers).json() == [series.id]


def test_favorites_are_private_and_validated(client: TestClient, titles: list[Title]) -> None:
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    client.put(f"/api/v1/me/favorites/{titles[0].id}", headers=alice)

    assert client.get("/api/v1/me/favorites", headers=bob).json() == []
    assert client.put("/api/v1/me/favorites/9999", headers=alice).status_code == 404
    assert client.get("/api/v1/me/favorites").status_code == 401
