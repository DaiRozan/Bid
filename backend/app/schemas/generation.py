"""Model output is a composition of frozen facts and approved generic methods."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactPart(StrictModel):
    kind: Literal["fact"]
    fact_id: str
    field: Literal["value", "name", "unit_project", "features", "quantity", "unit"] = "value"


class MethodPart(StrictModel):
    kind: Literal["method"]
    # Closed vocabulary: arbitrary prose cannot smuggle new project properties.
    text: Literal[
        "组织分区流水施工。", "依据上述固定事实编制施工安排。",
        "施工前核对图纸、清单与补疑，发现差异及时记录并提请确认。",
        "按照已确认的施工范围组织作业，落实工序交接。",
        "建立进度检查机制，协调人员、材料与机械进场。",
        "结合现场条件编制作业计划，经审批后实施。",
        "做好测量复核，保护控制点，保存测量记录。",
        "核对作业面与相邻工序的关系，落实交叉作业协调。",
        "开展技术交底，明确作业程序、质量要求与验收责任。",
        "材料进场核验质量证明文件，按要求复验并分类存放。",
        "落实工序自检、交接检查及隐蔽验收，保留可追溯记录。",
        "对关键工序实施过程检查，发现问题及时整改并复核。",
        "未经确认的工程参数、数量和施工条件应列为待确认事项。",
        "施工方案中的专项参数经核算及审批后执行。",
        "开展安全教育与风险辨识，落实作业许可和现场防护。",
        "检查临时用电、机械设备及作业环境，发现隐患立即处理。",
        "落实扬尘、噪声与污水控制，保持现场整洁。",
        "按已批准的应急预案组织响应，保持联络与通道畅通。",
        "落实成品保护，协调后续工序，防止交叉作业损坏。",
        "整理检验、验收和变更资料，确保记录与实际施工一致。",
        "严格执行已固定的招标编制要求。",
    ]


Part = Annotated[FactPart | MethodPart, Field(discriminator="kind")]


class GeneratedParagraph(StrictModel):
    type: Literal["paragraph"]
    parts: list[Part] = Field(min_length=1)


class GeneratedTable(StrictModel):
    type: Literal["table"]
    rows: list[list[list[Part]]] = Field(min_length=1)


class Generated(StrictModel):
    blocks: list[Annotated[GeneratedParagraph | GeneratedTable, Field(discriminator="type")]] = Field(min_length=1)
    open_issues: list[str] = Field(default_factory=list)
