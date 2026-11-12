"""Admin panel API."""

import json
import shutil
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Country, Genre, Payment, PaymentScenario, PaymentStatus, User, UserRole
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.services.billing.plan_service import PlanService


def register(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "admin-pass-1", "display_name": email[:5]})  # fmt: skip
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "admin-pass-1"}
                        ).json()["access_token"]  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(client: TestClient, session: Session) -> dict[str, str]:
    headers = register(client, "boss@example.com")
    user = session.scalars(select(User).where(User.email == "boss@example.com")).one()
    user.role = UserRole.ADMIN
    session.commit()
    return headers


@pytest.fixture
def refs(session: Session) -> dict:
    drama, anim = Genre(name="Драма"), Genre(name="Мультфільм")
    ua = Country(code="UA", name="Україна")
    session.add_all([drama, anim, ua])
    session.commit()
    return {"drama": drama.id, "anim": anim.id}


def movie_body(refs: dict, **overrides) -> dict:
    return {
        "type": "movie", "title": "Тіні забутих предків", "description": "Карпатська легенда.",
        "release_year": 1965, "rating": "7.6", "duration": 97,
        "genre_ids": [refs["drama"]], "country_codes": ["ua"],
    } | overrides  # fmt: skip


def test_admin_endpoints_require_the_admin_role(client: TestClient, refs: dict) -> None:
    viewer = register(client, "viewer@example.com")

    assert client.post("/api/v1/admin/titles", json=movie_body(refs), headers=viewer
                       ).status_code == 403  # fmt: skip
    assert client.get("/api/v1/admin/users", headers=viewer).status_code == 403
    assert client.get("/api/v1/admin/users").status_code == 401


def test_title_create_update_delete(client: TestClient, admin: dict, refs: dict) -> None:
    created = client.post("/api/v1/admin/titles", json=movie_body(refs), headers=admin)
    assert created.status_code == 201
    title = created.json()
    assert (title["title"], title["rating"], [c["code"] for c in title["countries"]]) == (
        "Тіні забутих предків", "7.6", ["UA"])  # fmt: skip

    updated = client.put(f"/api/v1/admin/titles/{title['id']}", headers=admin,
                         json=movie_body(refs, title="Тіні", genre_ids=[refs["anim"]]))  # fmt: skip
    assert updated.json()["title"] == "Тіні"
    assert [g["name"] for g in updated.json()["genres"]] == ["Мультфільм"]
    # The public catalog shows the change at once.
    assert client.get(f"/api/v1/catalog/titles/{title['id']}").json()["title"] == "Тіні"

    bad = client.put(f"/api/v1/admin/titles/{title['id']}", headers=admin,
                     json=movie_body(refs, genre_ids=[999]))  # fmt: skip
    assert bad.status_code == 404

    assert client.delete(f"/api/v1/admin/titles/{title['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/v1/catalog/titles/{title['id']}").status_code == 404


def test_title_validation(client: TestClient, admin: dict, refs: dict) -> None:
    for broken in ({"title": ""}, {"rating": "11"}, {"release_year": 1500}, {"type": "cartoon"}):
        response = client.post("/api/v1/admin/titles", json=movie_body(refs, **broken),
                               headers=admin)  # fmt: skip
        assert response.status_code == 422, broken


def test_seasons_and_episodes(client: TestClient, admin: dict, refs: dict) -> None:
    series = client.post("/api/v1/admin/titles", headers=admin,
                         json=movie_body(refs, type="series", title="Серіал")).json()  # fmt: skip
    movie = client.post("/api/v1/admin/titles", json=movie_body(refs), headers=admin).json()

    season = client.post(f"/api/v1/admin/titles/{series['id']}/seasons",
                         json={"number": 1, "name": "Сезон 1"}, headers=admin)  # fmt: skip
    assert season.status_code == 201
    season_id = season.json()["id"]
    duplicate = client.post(f"/api/v1/admin/titles/{series['id']}/seasons",
                            json={"number": 1, "name": "Ще раз"}, headers=admin)  # fmt: skip
    assert duplicate.status_code == 409
    assert client.post(f"/api/v1/admin/titles/{movie['id']}/seasons",
                       json={"number": 1, "name": "X"}, headers=admin).status_code == 409  # fmt: skip

    episode = client.post(f"/api/v1/admin/seasons/{season_id}/episodes", headers=admin,
                          json={"number": 1, "name": "Пілот", "duration": 45}).json()  # fmt: skip
    client.put(f"/api/v1/admin/episodes/{episode['id']}", headers=admin,
               json={"number": 1, "name": "Пілотна серія", "duration": 47})  # fmt: skip
    detail = client.get(f"/api/v1/catalog/titles/{series['id']}").json()
    assert detail["seasons"][0]["episodes"][0]["name"] == "Пілотна серія"

    assert client.delete(f"/api/v1/admin/seasons/{season_id}", headers=admin).status_code == 204
    assert client.get(f"/api/v1/catalog/titles/{series['id']}").json()["seasons"] == []


def test_import_without_tmdb_token_is_unavailable(client: TestClient, admin: dict) -> None:
    response = client.post("/api/v1/admin/titles/import", json={"tmdb_id": 603, "type": "movie"},
                           headers=admin)  # fmt: skip

    assert response.status_code == 503


@pytest.fixture
def stream() -> str:
    root = Settings.instance().hls_root
    directory = root / "admin-test-film"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "master.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
    (directory / "meta.json").write_text(json.dumps({"qualities": ["360p", "720p"],
                                                     "duration_sec": 600}))  # fmt: skip
    yield "admin-test-film"
    shutil.rmtree(directory)


def test_attach_and_detach_videos(client: TestClient, admin: dict, refs: dict, stream: str) -> None:
    movie = client.post("/api/v1/admin/titles", json=movie_body(refs), headers=admin).json()
    series = client.post("/api/v1/admin/titles", headers=admin,
                         json=movie_body(refs, type="series", title="Серіал")).json()  # fmt: skip
    season = client.post(f"/api/v1/admin/titles/{series['id']}/seasons",
                         json={"number": 2, "name": "С2"}, headers=admin).json()  # fmt: skip
    episode = client.post(f"/api/v1/admin/seasons/{season['id']}/episodes",
                          json={"number": 5, "name": "Е5"}, headers=admin).json()  # fmt: skip

    streams = client.get("/api/v1/admin/streams", headers=admin).json()
    assert {"directory": stream, "hls_path": f"{stream}/master.m3u8",
            "qualities": ["360p", "720p"], "duration_sec": 600} in streams  # fmt: skip

    attached = client.put(f"/api/v1/admin/titles/{movie['id']}/video",
                          json={"stream_dir": stream}, headers=admin).json()  # fmt: skip
    client.put(f"/api/v1/admin/episodes/{episode['id']}/video", json={"stream_dir": stream},
               headers=admin)  # fmt: skip
    videos = client.get("/api/v1/admin/videos", headers=admin).json()
    assert {(v["title"], v["episode_label"]) for v in videos} == {
        ("Тіні забутих предків", None), ("Серіал", "S2E5: Е5")}  # fmt: skip
    assert client.get(f"/api/v1/catalog/titles/{movie['id']}").json()["has_video"] is True

    assert client.put(f"/api/v1/admin/titles/{series['id']}/video", json={"stream_dir": stream},
                      headers=admin).status_code == 409  # fmt: skip
    assert client.put(f"/api/v1/admin/titles/{movie['id']}/video", json={"stream_dir": "nope"},
                      headers=admin).status_code == 404  # fmt: skip
    assert client.put(f"/api/v1/admin/titles/{movie['id']}/video",
                      json={"stream_dir": "../source"}, headers=admin).status_code == 422  # fmt: skip

    assert client.delete(f"/api/v1/admin/videos/{attached['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/v1/catalog/titles/{movie['id']}").json()["has_video"] is False


def test_ads_are_registered_and_toggled(client: TestClient, admin: dict, stream: str) -> None:
    ad = client.post("/api/v1/admin/ads", json={"name": "Знижка", "stream_dir": stream},
                     headers=admin).json()  # fmt: skip
    paused = client.patch(f"/api/v1/admin/ads/{ad['id']}", json={"active": False}, headers=admin)

    assert paused.json()["active"] is False
    assert [a["name"] for a in client.get("/api/v1/admin/ads", headers=admin).json()] == ["Знижка"]


def test_plan_settings_change_what_viewers_get(
    client: TestClient, admin: dict, session: Session
) -> None:
    PlanService(PlanRepository(session), SubscriptionRepository(session)).ensure_default_plans()
    premium = PlanRepository(session).get_by_code("premium")

    response = client.put(f"/api/v1/admin/plans/{premium.id}", headers=admin, json={
        "name": "Premium+", "price": "199.00", "period_days": 31, "max_quality": "1080p",
        "has_ads": False})  # fmt: skip

    assert response.status_code == 200
    plans = {p["code"]: p for p in client.get("/api/v1/plans").json()}
    assert (plans["premium"]["name"], plans["premium"]["price"]) == ("Premium+", "199.00")
    assert client.put(f"/api/v1/admin/plans/{premium.id}", headers=admin, json={
        "name": "X", "price": "1", "period_days": 30, "max_quality": "4k", "has_ads": False}
    ).status_code == 422  # fmt: skip


def test_users_search_roles_and_deletion(client: TestClient, admin: dict, session: Session) -> None:
    register(client, "anna@example.com")
    register(client, "payer@example.com")
    PlanService(PlanRepository(session), SubscriptionRepository(session)).ensure_default_plans()
    payer = session.scalars(select(User).where(User.email == "payer@example.com")).one()
    session.add(Payment(user_id=payer.id, plan_id=PlanRepository(session).get_by_code("premium").id,
                        amount=Decimal("149"), provider="mock", scenario=PaymentScenario.SUCCESS,
                        status=PaymentStatus.SUCCEEDED))  # fmt: skip
    session.commit()
    boss = session.scalars(select(User).where(User.email == "boss@example.com")).one()

    page = client.get("/api/v1/admin/users", params={"q": "ANNA"}, headers=admin).json()
    assert [u["email"] for u in page["items"]] == ["anna@example.com"] and page["total"] == 1
    anna_id = page["items"][0]["id"]

    promoted = client.patch(f"/api/v1/admin/users/{anna_id}", json={"role": "admin"}, headers=admin)
    assert promoted.json()["role"] == "admin"
    assert client.patch(f"/api/v1/admin/users/{boss.id}", json={"role": "user"},
                        headers=admin).status_code == 409  # fmt: skip

    assert client.delete(f"/api/v1/admin/users/{payer.id}", headers=admin).status_code == 409
    assert client.delete(f"/api/v1/admin/users/{boss.id}", headers=admin).status_code == 409
    assert client.delete(f"/api/v1/admin/users/{anna_id}", headers=admin).status_code == 204
    assert client.get("/api/v1/admin/users", params={"q": "anna"}, headers=admin).json()["total"] == 0
