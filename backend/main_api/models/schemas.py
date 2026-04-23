from pydantic import BaseModel
from typing import Literal


class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool


class AssistantChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantMaterialContext(BaseModel):
    title: str
    subject: str | None = None
    description: str | None = None
    objectives: str | None = None


class AssistantChatRequest(BaseModel):
    """
    助教对话请求（全局单会话，历史由前端维护并在每次请求时透传）。
    """

    messages: list[AssistantChatMessage]
    user_id: str = "default_user"
    kb_file_ids: list[str] | None = None
    material: AssistantMaterialContext | None = None
    language: str = "zh"


class LessonPlanProcedureStep(BaseModel):
    step: str
    duration: str
    activity: str


class LessonPlan(BaseModel):
    """
    LessonPlan（与 frontend/types.ts 对齐）
    """

    title: str
    targetAudience: str
    duration: str
    objectives: list[str]
    materials: list[str]
    procedure: list[LessonPlanProcedureStep]
    homework: str


class LessonPlanRequest(BaseModel):
    title: str
    subject: str | None = None
    description: str | None = None
    objectives: str | None = None
    outlineContent: str
    language: str = "zh"
    sessionId: str | None = None
    user_id: str | None = None
    kb_file_ids: list[str] | None = None
    # 教案内容模板（用于影响生成策略/结构，保持与前端 camelCase 一致）
    templateId: str | None = None


class LessonStyle(BaseModel):
    """
    Lesson 导出样式（V1）
    - 作为"展示/导出层"参数，不参与 LessonPlan 内容生成
    """

    fontZh: str = "微软雅黑"
    titleSizePt: int = 20
    h1SizePt: int = 16
    h2SizePt: int = 14
    bodySizePt: int = 12
    lineSpacing: float = 1.5

    # 页边距（cm）
    marginTopCm: float = 2.54
    marginBottomCm: float = 2.54
    marginLeftCm: float = 2.54
    marginRightCm: float = 2.54


class LessonExportDocxRequest(BaseModel):
    lessonPlan: LessonPlan
    style: LessonStyle | None = None
    language: str | None = None
    # 教案 docx 导出模板（与前端保持 camelCase）
    templateId: str | None = None
    # 可选：导出文件持久化到 artifacts（与前端保持 camelCase）
    userId: str | None = None
    materialId: str | None = None
    persist: bool | None = None
