from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class StoredAnalysis:
    analysis_id: str
    project_id: str
    created_at: datetime
    result: dict[str, Any]


class InMemoryAnalysisStore:
    def __init__(self) -> None:
        self._analyses: dict[str, StoredAnalysis] = {}

    def save(
        self, analysis_id: str, project_id: str, result: dict[str, Any]
    ) -> StoredAnalysis:
        analysis = StoredAnalysis(
            analysis_id=analysis_id,
            project_id=project_id,
            created_at=datetime.now(timezone.utc),
            result=result,
        )
        self._analyses[analysis_id] = analysis
        return analysis

    def get(self, analysis_id: str) -> StoredAnalysis | None:
        return self._analyses.get(analysis_id)

    def list_projects(self) -> list[dict[str, str]]:
        project_ids = sorted({analysis.project_id for analysis in self._analyses.values()})
        return [{"id": project_id, "name": project_id} for project_id in project_ids]
