import json
from collections.abc import Mapping
from typing import Any

from clustermind_engine.models import AnalysisResult, AttributeChange, ResourceChange

SUPPORTED_FORMAT_MAJOR = 1
_REDACTED = "[REDACTED]"
_UNKNOWN = "[UNKNOWN]"
_ACTIONS = {"create", "read", "update", "delete", "no-op"}


class PlanValidationError(ValueError):
    """Raised when a Terraform plan JSON document is unsupported or malformed."""


def parse_plan_json(payload: str | bytes) -> AnalysisResult:
    try:
        document = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as error:
        raise PlanValidationError("Terraform plan must be valid JSON") from error
    return parse_plan_document(document)


def parse_plan_document(document: Mapping[str, Any]) -> AnalysisResult:
    if not isinstance(document, Mapping):
        raise PlanValidationError("Terraform plan must be a JSON object")

    format_version = document.get("format_version")
    _validate_format_version(format_version)
    raw_resources = document.get("resource_changes")
    if not isinstance(raw_resources, list):
        raise PlanValidationError("Terraform plan resource_changes must be a list")

    resources: list[ResourceChange] = []
    for index, raw_resource in enumerate(raw_resources):
        resources.append(_normalize_resource(raw_resource, index))

    summary = {"create": 0, "update": 0, "delete": 0, "replace": 0, "no-op": 0}
    for resource in resources:
        if resource.action in summary:
            summary[resource.action] += 1

    return AnalysisResult(
        format_version=format_version,
        resources=tuple(resources),
        summary=summary,
    )


def _validate_format_version(format_version: Any) -> None:
    if not isinstance(format_version, str):
        raise PlanValidationError("Terraform plan format_version must be a string")
    try:
        major_version = int(format_version.split(".", 1)[0])
    except (TypeError, ValueError) as error:
        raise PlanValidationError("Terraform plan format_version is invalid") from error
    if major_version != SUPPORTED_FORMAT_MAJOR:
        raise PlanValidationError(
            f"Unsupported Terraform plan format major version: {format_version}"
        )


def _normalize_resource(raw_resource: Any, index: int) -> ResourceChange:
    if not isinstance(raw_resource, Mapping):
        raise PlanValidationError(f"resource_changes[{index}] must be an object")

    address = raw_resource.get("address")
    resource_type = raw_resource.get("type")
    change = raw_resource.get("change")
    if not isinstance(address, str) or not address:
        raise PlanValidationError(f"resource_changes[{index}].address must be a string")
    if not isinstance(resource_type, str) or not resource_type:
        raise PlanValidationError(f"resource_changes[{index}].type must be a string")
    if not isinstance(change, Mapping):
        raise PlanValidationError(f"resource_changes[{index}].change must be an object")

    actions = change.get("actions")
    if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
        raise PlanValidationError(f"resource_changes[{index}].change.actions must be a list")
    action = _normalize_action(actions)
    before = _safe_value(change.get("before"), change.get("before_sensitive"))
    after = _safe_value(
        change.get("after"),
        change.get("after_sensitive"),
        change.get("after_unknown"),
    )
    attribute_changes = _diff_values(before, after)
    changed_paths = {item.path for item in attribute_changes}
    sensitive_paths = _mask_paths(
        change.get("before_sensitive"), change.get("after_sensitive")
    )
    for raw_change in _diff_values(change.get("before"), change.get("after")):
        if raw_change.path in sensitive_paths and raw_change.path not in changed_paths:
            attribute_changes.append(
                AttributeChange(
                    path=raw_change.path,
                    before=_REDACTED,
                    after=_REDACTED,
                )
            )
    attribute_changes.sort(key=lambda item: item.path)

    return ResourceChange(
        address=address,
        resource_type=resource_type,
        action=action,
        module_address=_optional_string(raw_resource.get("module_address")),
        provider_name=_optional_string(raw_resource.get("provider_name")),
        attribute_changes=tuple(attribute_changes),
    )


def _normalize_action(actions: list[str]) -> str:
    unknown_actions = set(actions) - _ACTIONS
    if unknown_actions:
        raise PlanValidationError(f"Unsupported Terraform resource action: {sorted(unknown_actions)}")
    if "create" in actions and "delete" in actions:
        return "replace"
    if len(actions) == 1:
        return actions[0]
    raise PlanValidationError(f"Unsupported Terraform resource action sequence: {actions}")


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _safe_value(value: Any, sensitive: Any = None, unknown: Any = None) -> Any:
    if unknown is True:
        return _UNKNOWN
    if sensitive is True:
        return _REDACTED
    if isinstance(value, Mapping):
        sensitive_map = sensitive if isinstance(sensitive, Mapping) else {}
        unknown_map = unknown if isinstance(unknown, Mapping) else {}
        return {
            key: _safe_value(
                value.get(key), sensitive_map.get(key), unknown_map.get(key)
            )
            for key in sorted(set(value) | set(sensitive_map) | set(unknown_map))
        }
    if isinstance(sensitive, Mapping) or isinstance(unknown, Mapping):
        return _safe_value(
            value if isinstance(value, Mapping) else {}, sensitive, unknown
        )
    if isinstance(value, list):
        sensitive_items = sensitive if isinstance(sensitive, list) else []
        unknown_items = unknown if isinstance(unknown, list) else []
        return [
            _safe_value(
                item,
                sensitive_items[index] if index < len(sensitive_items) else None,
                unknown_items[index] if index < len(unknown_items) else None,
            )
            for index, item in enumerate(value)
        ]
    return value


def _mask_paths(before_sensitive: Any, after_sensitive: Any, path: str = "") -> set[str]:
    if before_sensitive is True or after_sensitive is True:
        return {path or "value"}
    paths: set[str] = set()
    if isinstance(before_sensitive, Mapping) or isinstance(after_sensitive, Mapping):
        before_map = before_sensitive if isinstance(before_sensitive, Mapping) else {}
        after_map = after_sensitive if isinstance(after_sensitive, Mapping) else {}
        for key in set(before_map) | set(after_map):
            child_path = f"{path}.{key}" if path else str(key)
            paths.update(
                _mask_paths(before_map.get(key), after_map.get(key), child_path)
            )
    if isinstance(before_sensitive, list) or isinstance(after_sensitive, list):
        before_list = before_sensitive if isinstance(before_sensitive, list) else []
        after_list = after_sensitive if isinstance(after_sensitive, list) else []
        for index in range(max(len(before_list), len(after_list))):
            child_path = f"{path}[{index}]"
            paths.update(
                _mask_paths(
                    before_list[index] if index < len(before_list) else None,
                    after_list[index] if index < len(after_list) else None,
                    child_path,
                )
            )
    return paths


def _diff_values(before: Any, after: Any, path: str = "") -> list[AttributeChange]:
    if isinstance(before, Mapping) or isinstance(after, Mapping):
        before_map = before if isinstance(before, Mapping) else {}
        after_map = after if isinstance(after, Mapping) else {}
        changes: list[AttributeChange] = []
        for key in sorted(set(before_map) | set(after_map)):
            child_path = f"{path}.{key}" if path else str(key)
            changes.extend(_diff_values(before_map.get(key), after_map.get(key), child_path))
        return changes
    if isinstance(before, list) or isinstance(after, list):
        before_list = before if isinstance(before, list) else []
        after_list = after if isinstance(after, list) else []
        changes = []
        for index in range(max(len(before_list), len(after_list))):
            child_path = f"{path}[{index}]"
            old_value = before_list[index] if index < len(before_list) else None
            new_value = after_list[index] if index < len(after_list) else None
            changes.extend(_diff_values(old_value, new_value, child_path))
        return changes
    if before != after:
        return [AttributeChange(path=path or "value", before=before, after=after)]
    return []
