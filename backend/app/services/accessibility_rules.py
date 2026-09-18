"""无障碍专项检查判定规则。

检查标准（单项判定）：
- 未配置              -> 不符合
- 已配置 + 完好       -> 符合
- 已配置 + 轻微破损   -> 部分符合
- 已配置 + 严重损坏   -> 不符合

整体结论：任一不符合 -> 不达标；无不符合但有部分符合 -> 部分达标；全部符合 -> 达标。
达标率 = (符合×1 + 部分符合×0.5) / 检查项数 × 100。
"""

from app.core.constants import (
    ACCESSIBILITY_NOT_CONFIGURED,
    ACCESSIBILITY_VERDICT_SCORES,
    AccessibilityCondition,
    AccessibilityResult,
    AccessibilityVerdict,
)


def judge_item(configured: bool, condition: str | None) -> str:
    """按检查标准判定单个设施项。"""
    if not configured:
        return AccessibilityVerdict.FAILED.value
    if condition == AccessibilityCondition.GOOD.value:
        return AccessibilityVerdict.COMPLIANT.value
    if condition == AccessibilityCondition.MINOR.value:
        return AccessibilityVerdict.PARTIAL.value
    return AccessibilityVerdict.FAILED.value


def normalize_condition(configured: bool, condition: str | None) -> str:
    """未配置的设施统一记为「未配置」；已配置缺省按完好计。"""
    if not configured:
        return ACCESSIBILITY_NOT_CONFIGURED
    return condition or AccessibilityCondition.GOOD.value


def calc_score(verdicts: list[str]) -> float:
    """按判定结果折算百分制达标率。"""
    if not verdicts:
        return 0.0
    total = sum(ACCESSIBILITY_VERDICT_SCORES[verdict] for verdict in verdicts)
    return round(total / len(verdicts) * 100, 1)


def build_result(verdicts: list[str]) -> str:
    """由单项判定汇总整体结论。"""
    if AccessibilityVerdict.FAILED.value in verdicts:
        return AccessibilityResult.FAIL.value
    if AccessibilityVerdict.PARTIAL.value in verdicts:
        return AccessibilityResult.PARTIAL.value
    return AccessibilityResult.PASS.value
