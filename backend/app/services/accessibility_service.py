"""无障碍设施专项检查业务逻辑。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ACCESSIBILITY_ISSUE_DEADLINE_DAYS,
    ACCESSIBILITY_NOT_CONFIGURED,
    ACCESSIBILITY_REQUIRED_FACILITIES,
    OPEN_ISSUE_STATUSES,
    AccessibilityResult,
    AccessibilityVerdict,
    IssueCategory,
    IssueSeverity,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import AccessibilityCheck, Issue, Restroom
from app.schemas.accessibility import (
    AccessibilityCheckCreate,
    AccessibilityCheckOut,
    AccessibilityDistrictStat,
    AccessibilityRestroomStat,
    AccessibilitySummary,
)
from app.schemas.issue import IssueCreate
from app.services import accessibility_rules, issue_service, restroom_service

SORTABLE_FIELDS = {
    "check_time": AccessibilityCheck.check_time,
    "score": AccessibilityCheck.score,
    "inspector": AccessibilityCheck.inspector,
    "created_at": AccessibilityCheck.created_at,
}


def _normalize_items(items: list) -> list[dict]:
    """校验并登记设施明细：必检设施须全部覆盖，按检查标准逐项判定。"""
    if not items:
        raise DomainError("无障碍检查项不能为空")
    normalized: list[dict] = []
    seen: set[str] = set()
    for item in items:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        facility = data.get("facility")
        facility = facility.value if hasattr(facility, "value") else str(facility or "").strip()
        if facility in seen:
            raise DomainError(f"设施「{facility}」重复登记")
        seen.add(facility)
        configured = bool(data.get("configured", True))
        condition = data.get("condition")
        condition = condition.value if hasattr(condition, "value") else condition
        condition = accessibility_rules.normalize_condition(configured, condition)
        normalized.append(
            {
                "facility": facility,
                "configured": configured,
                "condition": condition,
                "verdict": accessibility_rules.judge_item(configured, condition),
                "remark": data.get("remark"),
            }
        )
    missing = [name for name in ACCESSIBILITY_REQUIRED_FACILITIES if name not in seen]
    if missing:
        raise DomainError("缺少必检设施：" + "、".join(missing))
    normalized.sort(key=lambda item: ACCESSIBILITY_REQUIRED_FACILITIES.index(item["facility"]))
    return normalized


def get_check(db: Session, check_id: int) -> AccessibilityCheck:
    check = db.get(AccessibilityCheck, check_id)
    if check is None:
        raise NotFoundError(f"无障碍检查记录 {check_id} 不存在")
    return check


def to_out(check: AccessibilityCheck) -> AccessibilityCheckOut:
    return AccessibilityCheckOut.model_validate(check)


def list_checks(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    inspector: str | None = None,
    result: str | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "check_time",
    order: str = "desc",
) -> tuple[list[AccessibilityCheck], int]:
    stmt = select(AccessibilityCheck)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == AccessibilityCheck.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(AccessibilityCheck.restroom_id == restroom_id)
    if inspector:
        stmt = stmt.where(AccessibilityCheck.inspector.like(f"%{inspector.strip()}%"))
    if result:
        stmt = stmt.where(AccessibilityCheck.result == result)
    if date_from:
        stmt = stmt.where(AccessibilityCheck.check_time >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(AccessibilityCheck.check_time <= datetime.combine(date_to, time.max))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                AccessibilityCheck.inspector.like(like),
                AccessibilityCheck.remark.like(like),
                AccessibilityCheck.restroom_id.in_(
                    select(Restroom.id).where(Restroom.name.like(like))
                ),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, AccessibilityCheck.check_time)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), AccessibilityCheck.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def _open_issue_exists(db: Session, restroom_id: int, facility: str) -> bool:
    """同一公厕同一设施已存在未闭环的整改事项时，不再重复建单。"""
    return bool(
        db.scalar(
            select(Issue.id)
            .where(
                Issue.restroom_id == restroom_id,
                Issue.accessibility_check_id.is_not(None),
                Issue.title.like(f"无障碍{facility}%"),
                Issue.status.in_(OPEN_ISSUE_STATUSES),
            )
            .limit(1)
        )
    )


def _create_rectification_issues(
    db: Session, check: AccessibilityCheck, failed_items: list[dict]
) -> list[Issue]:
    """不符合项自动生成待整改事项。"""
    created: list[Issue] = []
    for item in failed_items:
        facility = item["facility"]
        if _open_issue_exists(db, check.restroom_id, facility):
            continue
        condition_text = (
            "未配置该设施" if item["condition"] == ACCESSIBILITY_NOT_CONFIGURED else f"设施{item['condition']}"
        )
        detail = f"，现场备注：{item['remark']}" if item.get("remark") else ""
        issue = issue_service.create_issue(
            db,
            IssueCreate(
                restroom_id=check.restroom_id,
                title=f"无障碍{facility}{item['condition']}",
                description=(
                    f"无障碍专项检查（{check.check_time:%Y-%m-%d %H:%M}）发现："
                    f"{facility}{condition_text}，按检查标准判定为不符合{detail}。"
                ),
                category=IssueCategory.FACILITY,
                severity=IssueSeverity.SERIOUS,
                reporter=check.inspector,
                report_time=check.check_time,
                deadline=check.check_time + timedelta(days=ACCESSIBILITY_ISSUE_DEADLINE_DAYS),
                initial_remark="由无障碍专项检查自动生成，待派单整改",
            ),
        )
        issue.accessibility_check_id = check.id
        created.append(issue)
    if created:
        db.commit()
    return created


def create_check(db: Session, payload: AccessibilityCheckCreate) -> AccessibilityCheck:
    restroom_service.get_restroom(db, payload.restroom_id)
    items = _normalize_items(payload.items)
    verdicts = [item["verdict"] for item in items]
    check = AccessibilityCheck(
        restroom_id=payload.restroom_id,
        inspector=payload.inspector,
        check_time=payload.check_time or datetime.now(),
        items=items,
        total_items=len(items),
        compliant_count=verdicts.count(AccessibilityVerdict.COMPLIANT.value),
        partial_count=verdicts.count(AccessibilityVerdict.PARTIAL.value),
        failed_count=verdicts.count(AccessibilityVerdict.FAILED.value),
        score=accessibility_rules.calc_score(verdicts),
        result=accessibility_rules.build_result(verdicts),
        remark=payload.remark,
    )
    db.add(check)
    db.commit()
    db.refresh(check)

    failed_items = [item for item in items if item["verdict"] == AccessibilityVerdict.FAILED.value]
    _create_rectification_issues(db, check, failed_items)
    db.refresh(check)
    restroom_service.touch(db, payload.restroom_id)
    return check


def delete_check(db: Session, check_id: int) -> None:
    check = get_check(db, check_id)
    db.delete(check)
    db.commit()


def _open_issue_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Issue.restroom_id, func.count())
        .where(Issue.accessibility_check_id.is_not(None), Issue.status.in_(OPEN_ISSUE_STATUSES))
        .group_by(Issue.restroom_id)
    ).all()
    return {restroom_id: int(count) for restroom_id, count in rows}


def summary(db: Session) -> AccessibilitySummary:
    """按区域与公厕汇总无障碍达标率（公厕取最近一次检查结论）。"""
    restrooms = list(db.scalars(select(Restroom).order_by(Restroom.code)))
    checks = list(db.scalars(select(AccessibilityCheck)))
    open_counts = _open_issue_counts(db)

    latest: dict[int, AccessibilityCheck] = {}
    check_counts: dict[int, int] = {}
    for check in sorted(checks, key=lambda item: (item.check_time, item.id)):
        latest[check.restroom_id] = check
        check_counts[check.restroom_id] = check_counts.get(check.restroom_id, 0) + 1

    restroom_stats: list[AccessibilityRestroomStat] = []
    for restroom in restrooms:
        last = latest.get(restroom.id)
        restroom_stats.append(
            AccessibilityRestroomStat(
                restroom_id=restroom.id,
                code=restroom.code,
                name=restroom.name,
                district=restroom.district,
                check_count=check_counts.get(restroom.id, 0),
                last_check_time=last.check_time if last else None,
                last_result=last.result if last else "未检查",
                last_score=last.score if last else None,
                open_issue_count=open_counts.get(restroom.id, 0),
            )
        )

    district_stats: list[AccessibilityDistrictStat] = []
    by_district: dict[str, list[AccessibilityRestroomStat]] = {}
    for stat in restroom_stats:
        by_district.setdefault(stat.district, []).append(stat)
    for district, group in sorted(by_district.items()):
        inspected = [item for item in group if item.check_count > 0]
        compliant = sum(1 for item in inspected if item.last_result == AccessibilityResult.PASS.value)
        partial = sum(1 for item in inspected if item.last_result == AccessibilityResult.PARTIAL.value)
        failed = sum(1 for item in inspected if item.last_result == AccessibilityResult.FAIL.value)
        scores = [item.last_score for item in inspected if item.last_score is not None]
        district_stats.append(
            AccessibilityDistrictStat(
                district=district,
                restroom_count=len(group),
                inspected_count=len(inspected),
                uninspected_count=len(group) - len(inspected),
                compliant_count=compliant,
                partial_count=partial,
                failed_count=failed,
                pass_rate=round(compliant / len(group) * 100, 1) if group else 0.0,
                avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
                open_issue_count=sum(item.open_issue_count for item in group),
            )
        )

    return AccessibilitySummary(
        total_checks=len(checks),
        checked_restrooms=len(latest),
        total_restrooms=len(restrooms),
        compliant_items=sum(check.compliant_count for check in checks),
        partial_items=sum(check.partial_count for check in checks),
        failed_items=sum(check.failed_count for check in checks),
        pass_checks=sum(1 for check in checks if check.result == AccessibilityResult.PASS.value),
        partial_checks=sum(1 for check in checks if check.result == AccessibilityResult.PARTIAL.value),
        failed_checks=sum(1 for check in checks if check.result == AccessibilityResult.FAIL.value),
        avg_score=round(sum(check.score for check in checks) / len(checks), 1) if checks else 0.0,
        open_issue_count=sum(open_counts.values()),
        districts=district_stats,
        restrooms=restroom_stats,
    )
