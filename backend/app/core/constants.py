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
    ACCESSIBILITY = "无障碍设施"
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


class AccessibilityConformity(StrEnum):
    """无障碍设施单项/总体符合性判定。"""

    COMPLIANT = "符合"
    PARTIAL = "部分符合"
    NON_COMPLIANT = "不符合"


class AccessibilityCondition(StrEnum):
    """设施完好状态。"""

    GOOD = "完好"
    MINOR_DAMAGE = "轻微破损"
    SEVERE_DAMAGE = "严重损坏"


# 无障碍专项检查项：key 为稳定标识，standard 为判定依据的检查标准
ACCESSIBILITY_CHECK_ITEMS: list[dict[str, str]] = [
    {
        "key": "handrail",
        "name": "无障碍扶手",
        "standard": "坐便器两侧及洗手台应设置安全抓杆，安装牢固、高度适宜，无松动、锈蚀、缺失",
    },
    {
        "key": "ramp",
        "name": "无障碍坡道",
        "standard": "出入口应设置无障碍坡道，坡度不应大于 1:12，坡面平整防滑，两侧宜设扶手",
    },
    {
        "key": "tactile_path",
        "name": "盲道",
        "standard": "入口及周边盲道应连续贯通，无断头、无占用，砖体无破损、缺失",
    },
    {
        "key": "accessible_stall",
        "name": "无障碍专用间",
        "standard": "应设置无障碍专用厕位（间），门扇向外开启，内部回转空间充足，呼叫装置可用，标识清晰",
    },
]

ACCESSIBILITY_ITEM_MAP: dict[str, dict[str, str]] = {
    item["key"]: item for item in ACCESSIBILITY_CHECK_ITEMS
}

# 单项判定权重：符合计 1、部分符合计 0.5、不符合计 0，用于折算达标率
ACCESSIBILITY_CONFORMITY_WEIGHT: dict[str, float] = {
    AccessibilityConformity.COMPLIANT.value: 1.0,
    AccessibilityConformity.PARTIAL.value: 0.5,
    AccessibilityConformity.NON_COMPLIANT.value: 0.0,
}
