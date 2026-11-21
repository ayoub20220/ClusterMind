import json
from dataclasses import asdict
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status

from clustermind_engine.reporting import analyze_plan_document

from .schemas import AnalysisCreateResponse, AnalysisResponse, ProjectResponse
from .store import InMemoryAnalysisStore

MAX_PLAN_BYTES = 5 * 1024 * 1024

app = FastAPI(title="ClusterMind API", version="0.2.0")
store = InMemoryAnalysisStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.get("/api/v1/status")
def status_info() -> dict[str, str]:
    return {"status": "ready", "message": "Terraform analysis API is available."}


@app.get("/api/v1/projects", response_model=list[ProjectResponse])
def list_projects() -> list[dict[str, str]]:
    return store.list_projects()


@app.post(
    "/api/v1/analyses",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    plan: UploadFile = File(...),
    project_id: str = Query("default", min_length=1, max_length=100),
) -> AnalysisCreateResponse:
    if not _is_json_upload(plan):
        raise HTTPException(status_code=415, detail="Upload a Terraform plan JSON file")

    payload = await plan.read(MAX_PLAN_BYTES + 1)
    if len(payload) > MAX_PLAN_BYTES:
        raise HTTPException(status_code=413, detail="Terraform plan exceeds the 5 MB limit")

    try:
        document = _load_json(payload)
        report = analyze_plan_document(document)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    analysis_id = str(uuid4())
    store.save(analysis_id, project_id, _serialize_report(report))
    return AnalysisCreateResponse(
        analysis_id=analysis_id,
        project_id=project_id,
        status="completed",
    )


@app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str) -> AnalysisResponse:
    analysis = store.get(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisResponse(
        analysis_id=analysis.analysis_id,
        project_id=analysis.project_id,
        status="completed",
        created_at=analysis.created_at,
        result=analysis.result,
    )


def _is_json_upload(plan: UploadFile) -> bool:
    filename = (plan.filename or "").lower()
    content_type = (plan.content_type or "").lower()
    return filename.endswith(".json") or content_type == "application/json"


def _load_json(payload: bytes) -> dict:
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise ValueError("Terraform plan must be a JSON object")
    return document


def _serialize_report(report: object) -> dict:
    return asdict(report)
