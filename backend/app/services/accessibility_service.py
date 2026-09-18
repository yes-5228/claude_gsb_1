"""无障碍设施专项检查业务逻辑。

判定规则（按检查标准）：
- 未配置该设施 -> 不符合
- 已配置且完好 -> 符合
- 已配置但轻微破损 -> 部分符合
- 已配置但严重损坏 -> 不符合

总体判定：全部符合 -> 符合；存在不符合 -> 不符合；其余 -> 部分符合。
达标率 = (符合项数 × 1 + 部分符合项数 × 0.5) / 检查项数 × 100。
不符合项会自动生成「待整改」问题工单（同公厕同设施未闭环时不重复生成）。
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ACCESSIBILITY_CONFORMITY_WEIGHT,
    ACCESSIBILITY_ITEM_MAP,
    OPEN_ISSUE_STATUSES,
    AccessibilityCondition,
    AccessibilityConformity,
    IssueCategory,
    IssueSeverity,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import AccessibilityInspection, Issue, Restroom
from app.schemas.accessibility import (
    AccessibilityDistrictSummary,
    AccessibilityInspectionCreate,
    AccessibilityInspectionOut,
    AccessibilityInspectionUpdate,
    AccessibilityRestroomSummary,
    AccessibilitySummary,
    AccessibilitySummaryOverall,
)
from app.schemas.issue import IssueCreate
from app.services import issue_service, restroom_service

SORTABLE_FIELDS = {
    "inspect_time": AccessibilityInspection.inspect_time,
    "rate": AccessibilityInspection.rate,
    "inspector": AccessibilityInspection.inspector,
    "created_at": AccessibilityInspection.created_at,
}

# 不符合项生成工单时的严重程度与整改期限
ISSUE_SEVERITY_BY_REASON = {
    "missing": (IssueSeverity.SERIOUS, 3),  # 未配置：严重，3 天整改期
    "damaged": (IssueSeverity.NORMAL, 7),  # 严重损坏：一般，7 天整改期
}


def judge_item(configured: bool, condition: str | None) -> str:
    """按检查标准判定单项设施符合性。"""
    if not configured:
        return AccessibilityConformity.NON_COMPLIANT.value
    if condition == AccessibilityCondition.GOOD.value:
        return AccessibilityConformity.COMPLIANT.value
    if condition == AccessibilityCondition.MINOR_DAMAGE.value:
        return AccessibilityConformity.PARTIAL.value
    return AccessibilityConformity.NON_COMPLIANT.value


def evaluate(items: list[dict]) -> tuple[int, int, int, float, str]:
    """汇总单项判定，返回 (符合数, 部分符合数, 不符合数, 达标率, 总体判定)。"""
    compliant = sum(
        1 for item in items if item["conformity"] == AccessibilityConformity.COMPLIANT.value
    )
    partial = sum(
        1 for item in items if item["conformity"] == AccessibilityConformity.PARTIAL.value
    )
    non_compliant = len(items) - compliant - partial
    rate = (
        round(
            sum(ACCESSIBILITY_CONFORMITY_WEIGHT[item["conformity"]] for item in items)
            / len(items)
            * 100,
            1,
        )
        if items
        else 0.0
    )
    if non_compliant:
        conformity = AccessibilityConformity.NON_COMPLIANT.value
    elif partial:
        conformity = AccessibilityConformity.PARTIAL.value
    else:
        conformity = AccessibilityConformity.COMPLIANT.value
    return compliant, partial, non_compliant, rate, conformity


def _normalize_items(items: list) -> list[dict]:
    if not items:
        raise DomainError("无障碍检查项不能为空")
    normalized: list[dict] = []
    seen: set[str] = set()
    for item in items:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        key = str(data.get("key", "")).strip()
        spec = ACCESSIBILITY_ITEM_MAP.get(key)
        if spec is None:
            raise DomainError(
                f"未知的无障碍检查项 {key}，可选：{'、'.join(ACCESSIBILITY_ITEM_MAP)}"
            )
        if key in seen:
            raise DomainError(f"检查项 {spec['name']} 重复提交")
        seen.add(key)
        configured = bool(data.get("configured"))
        condition = data.get("condition")
        condition_value = condition.value if hasattr(condition, "value") else condition
        if configured and not condition_value:
            raise DomainError(f"检查项 {spec['name']} 已配置，请登记完好状态")
        if not configured:
            condition_value = None
        normalized.append(
            {
                "key": key,
                "name": spec["name"],
                "standard": spec["standard"],
                "configured": configured,
                "condition": condition_value,
                "conformity": judge_item(configured, condition_value),
                "remark": data.get("remark"),
            }
        )
    return normalized


def get_inspection(db: Session, inspection_id: int) -> AccessibilityInspection:
    inspection = db.get(AccessibilityInspection, inspection_id)
    if inspection is None:
        raise NotFoundError(f"无障碍检查记录 {inspection_id} 不存在")
    return inspection


def to_out(inspection: AccessibilityInspection) -> AccessibilityInspectionOut:
    return AccessibilityInspectionOut.model_validate(inspection)


def list_inspections(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    inspector: str | None = None,
    conformity: str | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "inspect_time",
    order: str = "desc",
) -> tuple[list[AccessibilityInspection], int]:
    stmt = select(AccessibilityInspection)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == AccessibilityInspection.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(AccessibilityInspection.restroom_id == restroom_id)
    if inspector:
        stmt = stmt.where(AccessibilityInspection.inspector.like(f"%{inspector.strip()}%"))
    if conformity:
        stmt = stmt.where(AccessibilityInspection.conformity == conformity)
    if date_from:
        stmt = stmt.where(
            AccessibilityInspection.inspect_time >= datetime.combine(date_from, time.min)
        )
    if date_to:
        stmt = stmt.where(
            AccessibilityInspection.inspect_time <= datetime.combine(date_to, time.max)
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                AccessibilityInspection.inspector.like(like),
                AccessibilityInspection.remark.like(like),
                AccessibilityInspection.restroom_id.in_(
                    select(Restroom.id).where(Restroom.name.like(like))
                ),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, AccessibilityInspection.inspect_time)
    stmt = stmt.order_by(
        column.desc() if order == "desc" else column.asc(), AccessibilityInspection.id.desc()
    )
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def _issue_title(item: dict) -> str:
    return f"{item['name']}不符合无障碍检查标准"


def _issue_description(inspection: AccessibilityInspection, item: dict) -> str:
    state = "未配置该设施" if not item["configured"] else f"完好状态：{item['condition']}"
    parts = [
        f"无障碍专项检查（{inspection.inspect_time:%Y-%m-%d %H:%M}）发现「{item['name']}」不符合检查标准。",
        f"检查标准：{item['standard']}",
        f"登记情况：{state}",
    ]
    if item.get("remark"):
        parts.append(f"现场备注：{item['remark']}")
    return "\n".join(parts)


def generate_rectification_issues(
    db: Session, inspection: AccessibilityInspection
) -> list[Issue]:
    """为不符合项生成待整改工单；同公厕同设施已有未闭环工单时不重复生成。"""
    created: list[Issue] = []
    for item in inspection.items:
        if item["conformity"] != AccessibilityConformity.NON_COMPLIANT.value:
            continue
        title = _issue_title(item)
        existing = db.scalar(
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.restroom_id == inspection.restroom_id,
                Issue.title == title,
                Issue.category == IssueCategory.ACCESSIBILITY.value,
                Issue.status.in_(OPEN_ISSUE_STATUSES),
            )
        )
        if existing:
            continue
        severity, days = ISSUE_SEVERITY_BY_REASON[
            "missing" if not item["configured"] else "damaged"
        ]
        issue = issue_service.create_issue(
            db,
            IssueCreate(
                restroom_id=inspection.restroom_id,
                accessibility_inspection_id=inspection.id,
                title=title,
                description=_issue_description(inspection, item),
                category=IssueCategory.ACCESSIBILITY,
                severity=severity,
                reporter=inspection.inspector,
                deadline=inspection.inspect_time + timedelta(days=days),
                initial_remark="由无障碍专项检查自动生成的待整改事项",
            ),
        )
        created.append(issue)
    return created


def create_inspection(
    db: Session, payload: AccessibilityInspectionCreate
) -> AccessibilityInspection:
    restroom_service.get_restroom(db, payload.restroom_id)
    items = _normalize_items(payload.items)
    compliant, partial, non_compliant, rate, conformity = evaluate(items)
    inspection = AccessibilityInspection(
        restroom_id=payload.restroom_id,
        inspector=payload.inspector,
        inspect_time=payload.inspect_time or datetime.now(),
        items=items,
        compliant_count=compliant,
        partial_count=partial,
        non_compliant_count=non_compliant,
        rate=rate,
        conformity=conformity,
        remark=payload.remark,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    generate_rectification_issues(db, inspection)
    db.refresh(inspection)
    restroom_service.touch(db, payload.restroom_id)
    return inspection


def update_inspection(
    db: Session, inspection_id: int, payload: AccessibilityInspectionUpdate
) -> AccessibilityInspection:
    inspection = get_inspection(db, inspection_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("items") is not None:
        items = _normalize_items(payload.items or [])
        compliant, partial, non_compliant, rate, conformity = evaluate(items)
        inspection.items = items
        inspection.compliant_count = compliant
        inspection.partial_count = partial
        inspection.non_compliant_count = non_compliant
        inspection.rate = rate
        inspection.conformity = conformity
    if data.get("inspector") is not None:
        inspection.inspector = payload.inspector or inspection.inspector
    if data.get("inspect_time") is not None and payload.inspect_time is not None:
        inspection.inspect_time = payload.inspect_time
    if "remark" in data:
        inspection.remark = payload.remark
    db.commit()
    db.refresh(inspection)
    return inspection


def delete_inspection(db: Session, inspection_id: int) -> None:
    inspection = get_inspection(db, inspection_id)
    db.delete(inspection)
    db.commit()


def _open_issue_counts(db: Session) -> dict[int, int]:
    """各公厕未闭环的无障碍整改事项数。"""
    rows = db.execute(
        select(Issue.restroom_id, func.count())
        .where(
            Issue.accessibility_inspection_id.is_not(None),
            Issue.status.in_(OPEN_ISSUE_STATUSES),
        )
        .group_by(Issue.restroom_id)
    ).all()
    return {restroom_id: int(count) for restroom_id, count in rows}


def build_summary(db: Session) -> AccessibilitySummary:
    """按区域与公厕汇总无障碍达标率。"""
    inspections = list(db.scalars(select(AccessibilityInspection)))
    restrooms = list(db.scalars(select(Restroom).order_by(Restroom.code)))
    open_counts = _open_issue_counts(db)

    by_restroom: dict[int, list[AccessibilityInspection]] = {}
    for inspection in inspections:
        by_restroom.setdefault(inspection.restroom_id, []).append(inspection)

    restroom_summaries: list[AccessibilityRestroomSummary] = []
    for restroom in restrooms:
        records = sorted(
            by_restroom.get(restroom.id, []),
            key=lambda item: (item.inspect_time, item.id),
            reverse=True,
        )
        latest = records[0] if records else None
        restroom_summaries.append(
            AccessibilityRestroomSummary(
                restroom_id=restroom.id,
                code=restroom.code,
                name=restroom.name,
                district=restroom.district,
                inspection_count=len(records),
                latest_inspect_time=latest.inspect_time if latest else None,
                latest_conformity=latest.conformity if latest else None,
                latest_rate=latest.rate if latest else None,
                avg_rate=(
                    round(sum(item.rate for item in records) / len(records), 1) if records else None
                ),
                open_issue_count=open_counts.get(restroom.id, 0),
            )
        )

    district_summaries: list[AccessibilityDistrictSummary] = []
    by_district: dict[str, list[AccessibilityRestroomSummary]] = {}
    for summary in restroom_summaries:
        by_district.setdefault(summary.district, []).append(summary)
    for district, group in by_district.items():
        inspected = [item for item in group if item.inspection_count > 0]
        district_summaries.append(
            AccessibilityDistrictSummary(
                district=district,
                restroom_count=len(group),
                inspected_count=len(inspected),
                compliant_count=sum(
                    1
                    for item in inspected
                    if item.latest_conformity == AccessibilityConformity.COMPLIANT.value
                ),
                partial_count=sum(
                    1
                    for item in inspected
                    if item.latest_conformity == AccessibilityConformity.PARTIAL.value
                ),
                non_compliant_count=sum(
                    1
                    for item in inspected
                    if item.latest_conformity == AccessibilityConformity.NON_COMPLIANT.value
                ),
                avg_rate=(
                    round(sum(item.latest_rate for item in inspected) / len(inspected), 1)
                    if inspected
                    else None
                ),
                open_issue_count=sum(item.open_issue_count for item in group),
            )
        )

    # 达标率低的区域/公厕排在前面，未检查的排在最后
    district_summaries.sort(
        key=lambda item: (item.avg_rate is None, item.avg_rate if item.avg_rate is not None else 0)
    )
    restroom_summaries.sort(
        key=lambda item: (
            item.latest_rate is None,
            item.latest_rate if item.latest_rate is not None else 0,
            -item.inspection_count,
        )
    )

    return AccessibilitySummary(
        overall=AccessibilitySummaryOverall(
            inspection_total=len(inspections),
            restroom_covered=len(by_restroom),
            item_total=sum(
                item.compliant_count + item.partial_count + item.non_compliant_count
                for item in inspections
            ),
            compliant_items=sum(item.compliant_count for item in inspections),
            partial_items=sum(item.partial_count for item in inspections),
            non_compliant_items=sum(item.non_compliant_count for item in inspections),
            avg_rate=(
                round(sum(item.rate for item in inspections) / len(inspections), 1)
                if inspections
                else 0.0
            ),
            open_issue_count=sum(open_counts.values()),
        ),
        districts=district_summaries,
        restrooms=restroom_summaries,
    )
