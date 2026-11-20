from clustermind_engine.health import health


def test_health() -> None:
    assert health() == {"status": "ok", "service": "engine"}
