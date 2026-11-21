from backend.app.main import health, status_info


def test_health() -> None:
    assert health() == {"status": "ok", "service": "backend"}


def test_status() -> None:
    assert status_info()["status"] == "ready"
