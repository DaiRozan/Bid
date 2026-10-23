from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.project import Project
from ..models.template import Template


def starter_items(engineering_type: str) -> list[dict]:
    if engineering_type == "municipal":
        titles = ["一、施工总体部署", "二、道路与排水工程", "三、交通组织与导改"]
    else:
        titles = ["一、施工总体部署", "二、主体结构施工", "三、机电与装饰工程"]
    return [{"title": title, "body": "", "required": True, "budget_pages": 2} for title in titles]


def get_outline(session: Session, project: Project) -> dict:
    template = session.scalar(select(Template).where(Template.engineering_type == project.engineering_type))
    if template is None:
        template = Template(engineering_type=project.engineering_type, items=starter_items(project.engineering_type))
        session.add(template)
        session.commit()
    return {"engineering_type": project.engineering_type, "items": template.items}


def save_outline(session: Session, project: Project, items: list[dict]) -> dict:
    template = session.scalar(select(Template).where(Template.engineering_type == project.engineering_type))
    if template is None:
        template = Template(engineering_type=project.engineering_type, items=items)
        session.add(template)
    else:
        template.items = items
    session.commit()
    return {"engineering_type": project.engineering_type, "items": template.items}

