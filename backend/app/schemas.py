from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProjectResponse(BaseModel):
    id: str
    name: str


class AnalysisCreateResponse(BaseModel):
    analysis_id: str
    project_id: str
    status: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    project_id: str
    status: str
    created_at: datetime
    result: dict[str, Any]
