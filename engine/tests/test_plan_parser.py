import json
from pathlib import Path

import pytest

from clustermind_engine.parser import PlanValidationError, parse_plan_document, parse_plan_json


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_plan.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normalizes_actions_and_summary() -> None:
    result = parse_plan_document(load_fixture())

    assert result.summary == {"create": 1, "update": 1, "delete": 0, "replace": 1, "no-op": 1}
    assert [resource.action for resource in result.resources] == [
        "create",
        "update",
        "replace",
        "no-op",
    ]
    assert result.resources[0].address == "azurerm_resource_group.example"
    assert result.resources[0].provider_name == "registry.terraform.io/hashicorp/azurerm"


def test_reports_safe_attribute_differences() -> None:
    result = parse_plan_document(load_fixture())
    storage_change = result.resources[1].attribute_changes

    assert [(change.path, change.before, change.after) for change in storage_change] == [
        ("access_key", "[REDACTED]", "[REDACTED]"),
        ("account_tier", "Standard", "Premium"),
    ]
    assert "old-secret" not in repr(result)
    assert "new-secret" not in repr(result)


def test_redacts_unknown_values() -> None:
    result = parse_plan_json(FIXTURE.read_bytes())

    resource = result.resources[0]
    unknown_changes = [
        change for change in resource.attribute_changes if change.path == "id"
    ]
    assert len(unknown_changes) == 1
    assert unknown_changes[0].after == "[UNKNOWN]"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"format_version": "2.0", "resource_changes": []}, "Unsupported"),
        ({"format_version": "1.0"}, "resource_changes"),
        ({"format_version": "1.0", "resource_changes": [{}]}, "address"),
    ],
)
def test_rejects_unsupported_or_malformed_plans(document: dict, message: str) -> None:
    with pytest.raises(PlanValidationError, match=message):
        parse_plan_document(document)


def test_rejects_invalid_json() -> None:
    with pytest.raises(PlanValidationError, match="valid JSON"):
        parse_plan_json("not-json")
