from dataclasses import dataclass
from typing import Any

from clustermind_engine.graph import DependencyGraph, build_dependency_graph
from clustermind_engine.models import AnalysisResult
from clustermind_engine.parser import parse_plan_document
from clustermind_engine.rules import Finding, evaluate_findings


@dataclass(frozen=True)
class AnalysisReport:
    result: AnalysisResult
    graph: DependencyGraph
    findings: tuple[Finding, ...]


def analyze_plan_document(document: dict[str, Any]) -> AnalysisReport:
    result = parse_plan_document(document)
    graph = build_dependency_graph(document)
    return AnalysisReport(
        result=result,
        graph=graph,
        findings=evaluate_findings(result, graph),
    )
