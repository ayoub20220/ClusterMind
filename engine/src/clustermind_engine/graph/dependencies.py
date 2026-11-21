from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    evidence: str


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[str, ...]
    edges: tuple[DependencyEdge, ...]

    def direct_dependencies(self, address: str) -> tuple[str, ...]:
        return tuple(sorted(edge.target for edge in self.edges if edge.source == address))

    def transitive_dependencies(self, address: str) -> tuple[str, ...]:
        adjacency = _adjacency(self.edges)
        visited: set[str] = set()
        queue = deque(adjacency.get(address, ()))
        while queue:
            dependency = queue.popleft()
            if dependency in visited:
                continue
            visited.add(dependency)
            queue.extend(adjacency.get(dependency, ()))
        return tuple(sorted(visited))

    def direct_dependents(self, address: str) -> tuple[str, ...]:
        return tuple(sorted(edge.source for edge in self.edges if edge.target == address))

    def transitive_dependents(self, address: str) -> tuple[str, ...]:
        reverse = _reverse_adjacency(self.edges)
        visited: set[str] = set()
        queue = deque(reverse.get(address, ()))
        while queue:
            dependent = queue.popleft()
            if dependent in visited:
                continue
            visited.add(dependent)
            queue.extend(reverse.get(dependent, ()))
        return tuple(sorted(visited))


def build_dependency_graph(document: Mapping[str, Any]) -> DependencyGraph:
    resource_addresses = {
        resource.get("address")
        for resource in _configuration_resources(document.get("configuration", {}))
        if isinstance(resource.get("address"), str)
    }
    resource_addresses.update(
        resource.get("address")
        for resource in document.get("resource_changes", [])
        if isinstance(resource, Mapping) and isinstance(resource.get("address"), str)
    )

    edges: set[DependencyEdge] = set()
    for resource in _configuration_resources(document.get("configuration", {})):
        address = resource.get("address")
        if not isinstance(address, str):
            continue
        for dependency in resource.get("depends_on", []):
            _add_edge(edges, address, dependency, "depends_on", resource_addresses)
        expressions = resource.get("expressions", {})
        if isinstance(expressions, Mapping):
            for name, expression in expressions.items():
                for reference in _expression_references(expression):
                    _add_edge(
                        edges,
                        address,
                        reference,
                        f"expression:{name}",
                        resource_addresses,
                    )

    return DependencyGraph(
        nodes=tuple(sorted(resource_addresses)),
        edges=tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.evidence))),
    )


def _configuration_resources(configuration: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(configuration, Mapping):
        return ()
    root_module = configuration.get("root_module", {})
    resources = root_module.get("resources", []) if isinstance(root_module, Mapping) else []
    modules = configuration.get("child_modules", [])
    result = [resource for resource in resources if isinstance(resource, Mapping)]
    for module in modules:
        result.extend(_configuration_resources({"root_module": module}))
    return result


def _expression_references(expression: Any) -> Iterable[str]:
    if not isinstance(expression, Mapping):
        return ()
    references = expression.get("references", [])
    return (reference for reference in references if isinstance(reference, str))


def _add_edge(
    edges: set[DependencyEdge],
    source: str,
    reference: Any,
    evidence: str,
    resource_addresses: set[str],
) -> None:
    if not isinstance(reference, str):
        return
    target = _resolve_address(reference, resource_addresses)
    if target and target != source:
        edges.add(DependencyEdge(source=source, target=target, evidence=evidence))


def _resolve_address(reference: str, resource_addresses: set[str]) -> str | None:
    candidates = [
        address
        for address in resource_addresses
        if reference == address
        or reference.startswith(f"{address}.")
        or reference.startswith(f"{address}[")
    ]
    return max(candidates, key=len, default=None)


def _adjacency(edges: Iterable[DependencyEdge]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.source].add(edge.target)
    return adjacency


def _reverse_adjacency(edges: Iterable[DependencyEdge]) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        reverse[edge.target].add(edge.source)
    return reverse
