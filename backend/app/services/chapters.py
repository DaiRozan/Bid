from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.chapter import Chapter, ChapterVersion
from ..models.project import Project


def append_version(session: Session, chapter: Chapter, blocks: list[dict], source: str, citations=None, open_issues=None) -> ChapterVersion:
    number = session.scalar(select(func.max(ChapterVersion.version_number)).where(ChapterVersion.chapter_id == chapter.id)) or 0
    version = ChapterVersion(
        chapter_id=chapter.id,
        version_number=number + 1,
        blocks=blocks,
        source=source,
        fact_version=session.get(Project, chapter.project_id).facts_version,
        citations=citations or [],
        open_issues=open_issues or [],
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


def serialize_chapter(session: Session, chapter: Chapter) -> dict:
    versions = list(session.scalars(select(ChapterVersion).where(ChapterVersion.chapter_id == chapter.id).order_by(ChapterVersion.version_number)))
    return {
        "id": chapter.id,
        "project_id": chapter.project_id,
        "title": chapter.title,
        "outline_position": chapter.outline_position,
        "stale": chapter.stale,
        "versions": [
            {
                "id": version.id,
                "version_number": version.version_number,
                "blocks": version.blocks,
                "source": version.source,
                "fact_version": version.fact_version,
                "citations": version.citations,
                "open_issues": version.open_issues,
            }
            for version in versions
        ],
    }

