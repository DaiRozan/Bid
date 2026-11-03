from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..db import get_db
from .fact_library import get_project
from ..services.site_analysis import analyze_site, load_report, report_entries

router = APIRouter(prefix="/api/projects/{project_id}/site-analysis", tags=["site-analysis"])


@router.get("")
def current(project_id: str, session: Session = Depends(get_db)):
    get_project(session, project_id)
    report = load_report(session, project_id)
    if not report:
        raise HTTPException(404, "尚未分析现场条件与施工影响")
    return report


@router.post("")
def analyze(project_id: str, session: Session = Depends(get_db)):
    try:
        project = get_project(session, project_id)
        report = analyze_site(session, project)
        from ..services.fact_library import write_draft
        write_draft(session, project)
        return report
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


class AdoptionRequest(BaseModel):
    analysis_id: str


@router.post("/adopt")
def adopt(project_id: str, body: AdoptionRequest, session: Session = Depends(get_db)):
    from ..models.fact_snapshot import FactAdoption
    project = get_project(session, project_id)
    report = load_report(session, project_id)
    if not report or report["stale"] or report["id"] != body.analysis_id:
        raise HTTPException(409, "请先分析当前资料；旧结果不能直接采用")
    entries = report_entries(report)
    existing = set(session.scalars(select(FactAdoption.target_id).where(FactAdoption.project_id == project.id)))
    for entry in entries:
        if entry["id"] not in existing:
            session.add(FactAdoption(project_id=project.id, target_id=entry["id"], value=entry["value"], reason="核对后采用现场分析，保留待核实条件", source_block_ids=entry["source_block_ids"]))
    session.commit()
    return {"adopted":len(entries), "message":"已纳入事实草稿，发布新版本后用于写作"}
