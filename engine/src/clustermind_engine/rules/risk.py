from dataclasses import dataclass

from clustermind_engine.graph import DependencyGraph
from clustermind_engine.models import AnalysisResult


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    confidence: str
    message: str
    evidence: tuple[str, ...]
    affected_resources: tuple[str, ...]
    recommendation: str


def evaluate_findings(result: AnalysisResult, graph: DependencyGraph) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for resource in result.resources:
        if resource.action not in {"delete", "replace"}:
            continue
        dependents = graph.transitive_dependents(resource.address)
        action_word = "replacement" if resource.action == "replace" else "deletion"
        findings.append(
            Finding(
                rule_id="destructive-resource-change",
                severity="high",
                confidence="high",
                message=f"Terraform proposes a {action_word} for {resource.address}.",
                evidence=(f"resource action: {resource.action}",),
                affected_resources=(resource.address,),
                recommendation="Review the planned change and its Terraform-declared dependents before deployment.",
            )
        )
        if dependents:
            findings.append(
                Finding(
                    rule_id="declared-dependent-impact",
                    severity="medium",
                    confidence="high",
                    message=f"{resource.address} has Terraform-declared dependents that may require review.",
                    evidence=(
                        "relationship: declared",
                        f"transitive dependents: {', '.join(dependents)}",
                    ),
                    affected_resources=(resource.address, *dependents),
                    recommendation="Review each declared dependent and its planned attributes before deployment.",
                )
            )
    return tuple(findings)
