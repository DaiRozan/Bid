import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models.chapter import Chapter, ChapterVersion
from ..models.fact import Fact
from ..models.knowledge_item import KnowledgeItem
from ..models.project import Project
from ..models.requirement import Requirement
from ..models.review_issue import ReviewIssue
from ..services.outlines import get_outline


def run_checks(session: Session, project: Project) -> list[dict]:
    session.execute(delete(ReviewIssue).where(ReviewIssue.project_id == project.id))
    issues: list[ReviewIssue] = []
    facts = list(session.scalars(select(Fact).where(Fact.project_id == project.id)))
    requirements = list(session.scalars(select(Requirement).where(Requirement.project_id == project.id)))
    chapters = list(session.scalars(select(Chapter).where(Chapter.project_id == project.id)))
    chapter_versions: dict[str, ChapterVersion | None] = {
        chapter.id: session.scalar(
            select(ChapterVersion).where(ChapterVersion.chapter_id == chapter.id).order_by(ChapterVersion.version_number.desc())
        )
        for chapter in chapters
    }

    name_fact = next((fact for fact in facts if fact.field_name in {"项目名称", "工程名称"} and fact.confirmed_value), None)
    if name_fact and name_fact.confirmed_value != project.name:
        issues.append(ReviewIssue(project_id=project.id, code="project_name_mismatch", message="项目名称与已确认事实不一致", severity="error"))
    duration_fact = next((fact for fact in facts if fact.field_name in {"工期", "计划工期"} and fact.confirmed_value), None)
    if duration_fact and not duration_fact.confirmed_value:
        issues.append(ReviewIssue(project_id=project.id, code="duration_missing", message="工期事实为空", severity="error"))

    outline = get_outline(session, project)
    titles = {chapter.title for chapter in chapters}
    for item in outline["items"]:
        if item.get("required") and item["title"] not in titles:
            issues.append(ReviewIssue(project_id=project.id, code="required_chapter_missing", message=f"缺少必选章节：{item['title']}", severity="error"))

    for requirement in requirements:
        if not requirement.response_chapter_id:
            issues.append(ReviewIssue(project_id=project.id, code="requirement_unmapped", message="编制要求尚未对应章节", location=requirement.id))

    for chapter in chapters:
        version = chapter_versions[chapter.id]
        if version is None:
            continue
        text = "\n".join(
            block.get("text", "") if block.get("type") == "paragraph" else "\n".join(" ".join(row) for row in block.get("rows", []))
            for block in version.blocks
        )
        if re.search(r"\{\{[^}]+\}\}|\[待[^]]+\]", text):
            issues.append(ReviewIssue(project_id=project.id, code="placeholder_found", message="正文仍有待替换占位符", location=chapter.title))
        if version.fact_version != project.facts_version:
            issues.append(ReviewIssue(project_id=project.id, code="stale_fact_version", message="章节依赖的事实版本已过期", location=chapter.title))
        for citation in version.citations:
            if isinstance(citation, dict) and citation.get("type") == "fact_library":
                from ..models.fact_snapshot import FactSnapshot
                snapshot = session.get(FactSnapshot, citation.get("snapshot_id"))
                if snapshot is None or snapshot.project_id != project.id:
                    issues.append(ReviewIssue(project_id=project.id, code="citation_missing", message="章节引用的固定事实库版本不存在", location=chapter.title))
                continue
            item_id = citation.get("knowledge_item_id") if isinstance(citation, dict) else None
            if not item_id or session.get(KnowledgeItem, item_id) is None:
                issues.append(ReviewIssue(project_id=project.id, code="citation_missing", message="章节引用资料不存在", location=chapter.title))
            elif session.get(KnowledgeItem, item_id).verification_status != "现行":
                issues.append(ReviewIssue(project_id=project.id, code="standard_unverified", message="引用规范尚未完成核验", location=chapter.title))

    session.add_all(issues)
    session.commit()
    return [
        {"id": issue.id, "code": issue.code, "severity": issue.severity, "message": issue.message, "location": issue.location, "status": issue.status}
        for issue in issues
    ]

