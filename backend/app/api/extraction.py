from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..adapters.deepseek import ModelConfigurationError, ModelResponseError
from ..db import get_db
from ..models.project import Project
from ..services.extraction import persist_extraction, run_extraction
from ..services.jobs import create_job
from ..schemas.extraction import ExtractionResult

router = APIRouter(prefix="/api/projects/{project_id}", tags=["extraction"])


@router.post("/extract")
def extract(project_id: str, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    job = create_job(session, project_id, "事实与要求抽取")
    job.status = "running"
    job.progress = 10
    session.commit()
    try:
        result = run_extraction(session, project)
        persist_extraction(session, project, ExtractionResult.model_validate(result))
        job.status = "succeeded"
        job.progress = 100
        session.commit()
        return {"job": job.__dict__ | {"_sa_instance_state": None}, "result": result}
    except ValueError as exc:
        job.status = "failed"
        job.error_message = str(exc)
        session.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ModelConfigurationError, ModelResponseError) as exc:
        job.status = "failed"
        job.error_message = str(exc)
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

