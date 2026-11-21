import json
from pathlib import Path

from backend.app.main import _load_json, _serialize_report, get_analysis, store
from clustermind_engine.reporting import analyze_plan_document


FIXTURE = Path(__file__).parents[2] / "engine" / "tests" / "fixtures" / "synthetic_plan.json"


def test_analysis_pipeline_serializes_safe_report() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = analyze_plan_document(document)
    serialized = _serialize_report(report)

    assert serialized["result"]["summary"]["replace"] == 1
    assert "old-secret" not in repr(serialized)
    assert serialized["findings"][0]["severity"] == "high"


def test_json_loader_rejects_non_object() -> None:
    try:
        _load_json(b"[]")
    except ValueError as error:
        assert str(error) == "Terraform plan must be a JSON object"
    else:
        raise AssertionError("non-object plan was accepted")


def test_store_returns_saved_analysis() -> None:
    saved = store.save("test-analysis", "test-project", {"summary": {}})

    assert get_analysis("test-analysis").analysis_id == saved.analysis_id
