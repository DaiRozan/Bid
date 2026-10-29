from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.project import Project
from ..services.fact_library import write_draft, publish_snapshot, load_snapshot, adopt_fact

router = APIRouter(prefix="/api/projects/{project_id}/fact-library", tags=["fact-library"])


def get_project(session, project_id):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "项目不存在")
    return project


class Publication(BaseModel):
    acknowledge_issues: bool = False


class Adoption(BaseModel):
    target_id: str
    value: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_block_ids: list[str] = Field(min_length=1)


@router.get("")
def draft(project_id: str, session: Session = Depends(get_db)):
    result, directory = write_draft(session, get_project(session, project_id))
    result.pop("_blocks")
    result.update(directory=str(directory), files=[str(p.relative_to(directory)).replace("\\", "/") for p in directory.rglob("*.md")])
    return result


@router.post("/publish", status_code=201)
def publish(project_id: str, body: Publication, session: Session = Depends(get_db)):
    try:
        return publish_snapshot(session, get_project(session, project_id), body.acknowledge_issues)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/current")
def current(project_id: str, session: Session = Depends(get_db)):
    try:
        return load_snapshot(session, get_project(session, project_id))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/adoptions", status_code=201)
def adopt(project_id: str, body: Adoption, session: Session = Depends(get_db)):
    try:
        record = adopt_fact(session, get_project(session, project_id), **body.model_dump())
        return {"id": record.id, "target_id": record.target_id}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/file")
def read_file(project_id: str, name: str, published: bool = False, session: Session = Depends(get_db)):
    project = get_project(session, project_id)
    if published:
        try:
            snapshot = load_snapshot(session, project)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        directory, files = Path(snapshot["directory"]), snapshot["files"]
    else:
        _, directory = write_draft(session, project)
        files = [str(p.relative_to(directory)).replace("\\", "/") for p in directory.rglob("*.md")]
    target = directory / name
    if name not in files or not target.resolve().is_relative_to(directory.resolve()):
        raise HTTPException(404, "事实库文件不存在")
    return {"name": name, "content": target.read_text(encoding="utf-8")}
