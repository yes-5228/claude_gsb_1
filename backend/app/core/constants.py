"""业务枚举与规则常量。"""

from enum import StrEnum


class RestroomStatus(StrEnum):
    NORMAL = "正常开放"
    MAINTENANCE = "维修中"
    CLOSED = "暂停使用"


class RestroomGrade(StrEnum):
    FIRST = "一类"
    SECOND = "二类"
    THIRD = "三类"


class Shift(StrEnum):
    MORNING = "早班"
    MIDDLE = "中班"
    NIGHT = "晚班"


class InspectionResult(StrEnum):
    NORMAL = "正常"
    ABNORMAL = "发现问题"


class IssueCategory(StrEnum):
    CLEANING = "保洁不到位"
    FACILITY = "设施损坏"
    ODOR = "异味扰民"
    CONSUMABLE = "耗材缺失"
    SAFETY = "安全隐患"
    OTHER = "其他"


class IssueSeverity(StrEnum):
    NORMAL = "一般"
    SERIOUS = "严重"
    URGENT = "紧急"


class IssueStatus(StrEnum):
    PENDING = "待整改"
    PROCESSING = "整改中"
    REVIEWING = "待验收"
    DONE = "已完成"
    CLOSED = "已关闭"


# 整改流转规则：当前状态 -> 允许流转到的状态
ISSUE_TRANSITIONS: dict[str, list[str]] = {
    IssueStatus.PENDING: [IssueStatus.PROCESSING, IssueStatus.CLOSED],
    IssueStatus.PROCESSING: [IssueStatus.REVIEWING, IssueStatus.CLOSED],
    IssueStatus.REVIEWING: [IssueStatus.DONE, IssueStatus.PROCESSING],
    IssueStatus.DONE: [IssueStatus.CLOSED],
    IssueStatus.CLOSED: [],
}

# 状态流转对应的动作名称，用于生成整改流水
TRANSITION_ACTIONS: dict[tuple[str, str], str] = {
    (IssueStatus.PENDING, IssueStatus.PROCESSING): "开始整改",
    (IssueStatus.PENDING, IssueStatus.CLOSED): "作废关闭",
    (IssueStatus.PROCESSING, IssueStatus.REVIEWING): "提交验收",
    (IssueStatus.PROCESSING, IssueStatus.CLOSED): "终止关闭",
    (IssueStatus.REVIEWING, IssueStatus.DONE): "验收通过",
    (IssueStatus.REVIEWING, IssueStatus.PROCESSING): "验收驳回",
    (IssueStatus.DONE, IssueStatus.CLOSED): "归档关闭",
}

# 巡查检查项，每项 0-10 分
INSPECTION_CHECK_ITEMS: list[str] = [
    "地面与台阶清洁",
    "便池蹲位清洁",
    "洗手台与镜面",
    "通风除臭",
    "耗材补充",
    "垃圾清运",
    "工具与标识摆放",
    "墙面门窗卫生",
]

INSPECTION_ITEM_MAX_SCORE = 10

GRADE_EXCELLENT = "优秀"
GRADE_GOOD = "良好"
GRADE_PASS = "合格"
GRADE_FAIL = "不合格"

# 仍处于整改闭环中的状态，用于统计未整改问题
OPEN_ISSUE_STATUSES: list[str] = [
    IssueStatus.PENDING,
    IssueStatus.PROCESSING,
    IssueStatus.REVIEWING,
]

# 单检查项低于该分数视为不合格项
INSPECTION_ITEM_PROBLEM_THRESHOLD = 6


class AccessibilityFacility(StrEnum):
    """无障碍专项检查的四类必检设施。"""

    HANDRAIL = "扶手"
    RAMP = "坡道"
    TACTILE = "盲道"
    STALL = "专用间"


class AccessibilityCondition(StrEnum):
    """设施完好状态（已配置时填写）。"""

    GOOD = "完好"
    MINOR = "轻微破损"
    SEVERE = "严重损坏"


# 未配置设施的完好状态统一记录为该值
ACCESSIBILITY_NOT_CONFIGURED = "未配置"


class AccessibilityVerdict(StrEnum):
    """单项设施按检查标准得出的判定结论。"""

    COMPLIANT = "符合"
    PARTIAL = "部分符合"
    FAILED = "不符合"


class AccessibilityResult(StrEnum):
    """一次专项检查的整体结论。"""

    PASS = "达标"
    PARTIAL = "部分达标"
    FAIL = "不达标"


# 检查标准要求的必检设施，登记时必须全部覆盖
ACCESSIBILITY_REQUIRED_FACILITIES: list[str] = [item.value for item in AccessibilityFacility]

# 判定取值：符合计 1、部分符合计 0.5、不符合计 0，用于折算达标率
ACCESSIBILITY_VERDICT_SCORES: dict[str, float] = {
    AccessibilityVerdict.COMPLIANT: 1.0,
    AccessibilityVerdict.PARTIAL: 0.5,
    AccessibilityVerdict.FAILED: 0.0,
}

# 无障碍问题自动建单时的默认整改期限（天）
ACCESSIBILITY_ISSUE_DEADLINE_DAYS = 7
