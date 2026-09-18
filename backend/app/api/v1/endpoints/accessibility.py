"""无障碍设施专项检查接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.accessibility import (
    AccessibilityCheckCreate,
    AccessibilityCheckOut,
    AccessibilitySummary,
)
from app.schemas.common import MessageOut, Page
from app.services import accessibility_service

router = APIRouter(prefix="/accessibility-checks", tags=["无障碍专项检查"])


@router.get("", response_model=Page[AccessibilityCheckOut], summary="专项检查记录列表")
def list_checks(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    inspector: Annotated[str | None, Query(description="检查人")] = None,
    result: Annotated[str | None, Query(description="检查结论：达标/部分达标/不达标")] = None,
    keyword: Annotated[str | None, Query(description="公厕名称/检查人/备注模糊搜索")] = None,
    date_from: Annotated[date | None, Query(description="开始日期")] = None,
    date_to: Annotated[date | None, Query(description="结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "check_time",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[AccessibilityCheckOut]:
    rows, total = accessibility_service.list_checks(
        db,
        restroom_id=restroom_id,
        district=district,
        inspector=inspector,
        result=result,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[AccessibilityCheckOut](
        items=[accessibility_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=AccessibilityCheckOut, status_code=201, summary="新增专项检查")
def create_check(
    payload: AccessibilityCheckCreate, db: Annotated[Session, Depends(get_db)]
) -> AccessibilityCheckOut:
    """登记四项设施的配置与完好状态，自动判定并就不符合项生成待整改事项。"""
    return accessibility_service.to_out(accessibility_service.create_check(db, payload))


@router.get("/summary", response_model=AccessibilitySummary, summary="无障碍达标率汇总")
def get_summary(db: Annotated[Session, Depends(get_db)]) -> AccessibilitySummary:
    """按区域与公厕汇总无障碍达标率（公厕取最近一次检查结论）。"""
    return accessibility_service.summary(db)


@router.get("/{check_id}", response_model=AccessibilityCheckOut, summary="专项检查详情")
def get_check(check_id: int, db: Annotated[Session, Depends(get_db)]) -> AccessibilityCheckOut:
    return accessibility_service.to_out(accessibility_service.get_check(db, check_id))


@router.delete("/{check_id}", response_model=MessageOut, summary="删除专项检查记录")
def delete_check(check_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    accessibility_service.delete_check(db, check_id)
    return MessageOut(message="删除成功")
