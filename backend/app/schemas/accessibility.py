"""无障碍设施专项检查相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AccessibilityCondition, AccessibilityFacility
from app.schemas.restroom import RestroomBrief


class AccessibilityItemIn(BaseModel):
    """登记单项设施的配置情况与完好状态。"""

    facility: AccessibilityFacility = Field(description="设施类型：扶手/坡道/盲道/专用间")
    configured: bool = Field(default=True, description="是否配置该设施")
    condition: AccessibilityCondition | None = Field(
        default=None, description="完好状态：完好/轻微破损/严重损坏；已配置时必填，缺省按完好计"
    )
    remark: str | None = Field(default=None, max_length=200, description="单项备注")


class AccessibilityItemOut(BaseModel):
    """单项设施登记结果，含按检查标准判定的结论。"""

    facility: str
    configured: bool
    condition: str = Field(description="完好状态，未配置时为「未配置」")
    verdict: str = Field(description="判定结论：符合/部分符合/不符合")
    remark: str | None = None


class AccessibilityCheckCreate(BaseModel):
    restroom_id: int
    inspector: str = Field(min_length=1, max_length=60, description="检查人")
    check_time: datetime | None = Field(default=None, description="检查时间，留空取当前时间")
    items: list[AccessibilityItemIn] = Field(
        min_length=1, description="设施登记明细，须覆盖全部必检设施"
    )
    remark: str | None = Field(default=None, max_length=500)


class AccessibilityIssueBrief(BaseModel):
    """由不符合项生成的待整改事项摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    status: str
    severity: str
    deadline: datetime | None = None
    report_time: datetime


class AccessibilityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restroom_id: int
    restroom: RestroomBrief | None = None
    inspector: str
    check_time: datetime
    items: list[AccessibilityItemOut] = Field(default_factory=list)
    total_items: int
    compliant_count: int
    partial_count: int
    failed_count: int
    score: float = Field(description="达标率（百分制）")
    result: str = Field(description="检查结论：达标/部分达标/不达标")
    remark: str | None = None
    created_at: datetime
    issues: list[AccessibilityIssueBrief] = Field(default_factory=list, description="生成的整改事项")


class AccessibilityRestroomStat(BaseModel):
    """单座公厕的无障碍达标情况（取最近一次检查）。"""

    restroom_id: int
    code: str
    name: str
    district: str
    check_count: int = Field(description="累计检查次数")
    last_check_time: datetime | None = None
    last_result: str = Field(default="未检查", description="最近一次检查结论")
    last_score: float | None = Field(default=None, description="最近一次达标率")
    open_issue_count: int = Field(default=0, description="未闭环的整改事项数")


class AccessibilityDistrictStat(BaseModel):
    """区域维度的无障碍达标率汇总。"""

    district: str
    restroom_count: int = Field(description="区域公厕总数")
    inspected_count: int = Field(description="已开展检查的公厕数")
    uninspected_count: int = Field(description="未检查公厕数")
    compliant_count: int = Field(description="最近检查达标的公厕数")
    partial_count: int = Field(description="最近检查部分达标的公厕数")
    failed_count: int = Field(description="最近检查不达标的公厕数")
    pass_rate: float = Field(description="达标率 = 达标公厕数 / 区域公厕总数 × 100")
    avg_score: float = Field(description="各公厕最近一次达标率的平均值")
    open_issue_count: int = Field(default=0, description="未闭环的整改事项数")


class AccessibilitySummary(BaseModel):
    """无障碍专项检查总览 + 区域/公厕两级汇总。"""

    total_checks: int = Field(description="累计检查次数")
    checked_restrooms: int = Field(description="已检查公厕数")
    total_restrooms: int = Field(description="公厕总数")
    compliant_items: int = Field(description="累计符合项数")
    partial_items: int = Field(description="累计部分符合项数")
    failed_items: int = Field(description="累计不符合项数")
    pass_checks: int = Field(description="结论为达标的检查次数")
    partial_checks: int = Field(description="结论为部分达标的检查次数")
    failed_checks: int = Field(description="结论为不达标的检查次数")
    avg_score: float = Field(description="全部检查的平均达标率")
    open_issue_count: int = Field(description="未闭环的整改事项数")
    districts: list[AccessibilityDistrictStat] = Field(default_factory=list)
    restrooms: list[AccessibilityRestroomStat] = Field(default_factory=list)
