from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_is_singleton() -> None:
    assert Settings.instance() is Settings.instance()
    assert get_settings() is Settings.instance()
