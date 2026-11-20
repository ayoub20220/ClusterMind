from fastapi import FastAPI

app = FastAPI(title="ClusterMind API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    return {"status": "scaffold", "message": "Analysis is not implemented yet."}
