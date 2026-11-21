import json
from pathlib import Path

from clustermind_engine.graph import build_dependency_graph
from clustermind_engine.reporting import analyze_plan_document


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_plan.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_builds_declared_edges_and_transitive_traversal() -> None:
    graph = build_dependency_graph(load_fixture())

    assert graph.direct_dependencies("azurerm_storage_account.example") == (
        "azurerm_resource_group.example",
    )
    assert graph.transitive_dependencies("azurerm_virtual_machine.example") == (
        "azurerm_network_interface.example",
        "azurerm_resource_group.example",
        "azurerm_storage_account.example",
    )
    assert graph.transitive_dependents("azurerm_network_interface.example") == (
        "azurerm_virtual_machine.example",
    )


def test_analysis_reports_destructive_change_and_declared_impact() -> None:
    report = analyze_plan_document(load_fixture())

    assert [finding.rule_id for finding in report.findings] == [
        "destructive-resource-change",
        "declared-dependent-impact",
    ]
    assert report.findings[0].severity == "high"
    assert report.findings[1].affected_resources == (
        "azurerm_network_interface.example",
        "azurerm_virtual_machine.example",
    )
    assert "relationship: declared" in report.findings[1].evidence


def test_graph_ignores_external_references() -> None:
    document = load_fixture()
    document["configuration"]["root_module"]["resources"][1]["expressions"][
        "resource_group_name"
    ]["references"].append("data.azurerm_client_config.current.subscription_id")

    graph = build_dependency_graph(document)

    assert all("data.azurerm_client_config.current" not in edge.target for edge in graph.edges)
