from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .db import init_db
from .api.projects import router as projects_router
from .api.documents import router as documents_router
from .api.facts import router as facts_router
from .api.requirements import router as requirements_router
from .api.knowledge import router as knowledge_router
from .api.jobs import router as jobs_router
from .api.extraction import router as extraction_router
from .api.outlines import router as outlines_router
from .api.chapters import router as chapters_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(title="技术标生成系统", version="0.1.0", lifespan=lifespan)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(facts_router)
app.include_router(requirements_router)
app.include_router(knowledge_router)
app.include_router(jobs_router)
app.include_router(extraction_router)
app.include_router(outlines_router)
app.include_router(chapters_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

