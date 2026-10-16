"""Small, stateless demo API. Replace these routes with your application."""
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Web Interface Starter", docs_url="/api/docs",
              openapi_url="/api/openapi.json", redoc_url=None)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=80)


@app.get("/api/health")
def health():
    return {"status": "ok", "instance": os.environ.get("STARTER_INSTANCE", ""),
            "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/projects")
def projects():
    return {"items": [
        {"name": "Market dashboard", "category": "Analytics", "status": "Example"},
        {"name": "Land explorer", "category": "Maps", "status": "Example"},
        {"name": "Automation console", "category": "Operations", "status": "Example"},
    ]}


@app.post("/api/preview")
def preview(request: PreviewRequest):
    title = request.title.strip()
    return {"title": title, "message": f'Ready to build: {title}', "saved": False}
