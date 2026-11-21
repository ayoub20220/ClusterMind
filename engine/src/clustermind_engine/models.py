from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AttributeChange:
    path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class ResourceChange:
    address: str
    resource_type: str
    action: str
    module_address: str | None = None
    provider_name: str | None = None
    attribute_changes: tuple[AttributeChange, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AnalysisResult:
    format_version: str
    resources: tuple[ResourceChange, ...]
    summary: dict[str, int]

