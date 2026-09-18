"""无障碍设施专项检查相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AccessibilityCondition
from app.schemas.restroom import RestroomBrief


class AccessibilityItemIn(BaseModel):
    """登记单项设施的配置情况与完好状态（符合性由服务端按检查标准判定）。"""

    key: str = Field(min_length=1, max_length=40, description="设施标识，见字典 accessibility_check_items")
    configured: bool = Field(description="是否已配置该设施")
    condition: AccessibilityCondition | None = Field(
        default=None, description="完好状态，已配置时必填"
    )
    remark: str | None = Field(default=None, max_length=200, description="单项备注")


class AccessibilityItemOut(BaseModel):
    """单项设施登记与判定结果。"""

    key: str
    name: str
    standard: str
    configured: bool
    condition: str | None = None
    conformity: str
    remark: str | None = None


class AccessibilityInspectionCreate(BaseModel):
    restroom_id: int
    inspector: str = Field(min_length=1, max_length=60, description="检查人")
    inspect_time: datetime | None = Field(default=None, description="检查时间，留空取当前时间")
    items: list[AccessibilityItemIn] = Field(min_length=1, description="设施登记明细")
    remark: str | None = Field(default=None, max_length=500)


class AccessibilityInspectionUpdate(BaseModel):
    inspector: str | None = Field(default=None, min_length=1, max_length=60)
    inspect_time: datetime | None = None
    items: list[AccessibilityItemIn] | None = Field(default=None, min_length=1)
    remark: str | None = Field(default=None, max_length=500)


class AccessibilityIssueBrief(BaseModel):
    """由不符合项生成的待整改事项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    status: str


class AccessibilityInspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restroom_id: int
    restroom: RestroomBrief | None = None
    inspector: str
    inspect_time: datetime
    items: list[AccessibilityItemOut] = Field(default_factory=list)
    compliant_count: int = 0
    partial_count: int = 0
    non_compliant_count: int = 0
    rate: float = Field(default=0.0, description="达标率（百分比）")
    conformity: str = Field(description="总体符合性判定")
    remark: str | None = None
    created_at: datetime
    issues: list[AccessibilityIssueBrief] = Field(default_factory=list, description="生成的整改事项")


class AccessibilityRestroomSummary(BaseModel):
    """按公厕汇总的无障碍达标情况。"""

    restroom_id: int
    code: str
    name: str
    district: str
    inspection_count: int = 0
    latest_inspect_time: datetime | None = None
    latest_conformity: str | None = None
    latest_rate: float | None = None
    avg_rate: float | None = Field(default=None, description="历次检查平均达标率")
    open_issue_count: int = Field(default=0, description="未闭环的无障碍整改事项数")


class AccessibilityDistrictSummary(BaseModel):
    """按区域汇总的无障碍达标情况。"""

    district: str
    restroom_count: int = 0
    inspected_count: int = Field(default=0, description="已开展无障碍检查的公厕数")
    compliant_count: int = Field(default=0, description="最近一次检查判定为符合的公厕数")
    partial_count: int = Field(default=0, description="最近一次检查判定为部分符合的公厕数")
    non_compliant_count: int = Field(default=0, description="最近一次检查判定为不符合的公厕数")
    avg_rate: float | None = Field(default=None, description="区域达标率（各公厕最近一次达标率的平均）")
    open_issue_count: int = Field(default=0, description="未闭环的无障碍整改事项数")


class AccessibilitySummaryOverall(BaseModel):
    inspection_total: int = 0
    restroom_covered: int = Field(default=0, description="已覆盖的公厕数")
    item_total: int = Field(default=0, description="累计登记设施项数")
    compliant_items: int = 0
    partial_items: int = 0
    non_compliant_items: int = 0
    avg_rate: float = Field(default=0.0, description="全部检查的平均达标率")
    open_issue_count: int = 0


class AccessibilitySummary(BaseModel):
    """无障碍达标率汇总：总体 + 按区域 + 按公厕。"""

    overall: AccessibilitySummaryOverall
    districts: list[AccessibilityDistrictSummary] = Field(default_factory=list)
    restrooms: list[AccessibilityRestroomSummary] = Field(default_factory=list)
