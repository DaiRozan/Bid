from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .db import init_db
from .api.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(title="技术标生成系统", version="0.1.0", lifespan=lifespan)
app.include_router(projects_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

