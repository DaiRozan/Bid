from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    url = get_settings().database_url
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, **kwargs)


def get_session_factory():
    return sessionmaker(bind=_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from .models.project import Project  # noqa: F401
    from .models.document import SourceDocument  # noqa: F401
    from .models.parse_block import ParseBlock  # noqa: F401
    from .models.fact import Fact  # noqa: F401
    from .models.requirement import Requirement  # noqa: F401
    from .models.knowledge_item import KnowledgeItem  # noqa: F401
    from .models.job import Job  # noqa: F401

    Base.metadata.create_all(_engine())

