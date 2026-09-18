"""无障碍设施专项检查接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.accessibility import (
    AccessibilityInspectionCreate,
    AccessibilityInspectionOut,
    AccessibilityInspectionUpdate,
    AccessibilitySummary,
)
from app.schemas.common import MessageOut, Page
from app.services import accessibility_service

router = APIRouter(prefix="/accessibility-inspections", tags=["无障碍专项检查"])


@router.get("", response_model=Page[AccessibilityInspectionOut], summary="无障碍检查记录列表")
def list_inspections(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    inspector: Annotated[str | None, Query(description="检查人")] = None,
    conformity: Annotated[str | None, Query(description="总体判定：符合/部分符合/不符合")] = None,
    keyword: Annotated[str | None, Query(description="公厕名称/备注模糊搜索")] = None,
    date_from: Annotated[date | None, Query(description="开始日期")] = None,
    date_to: Annotated[date | None, Query(description="结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "inspect_time",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[AccessibilityInspectionOut]:
    rows, total = accessibility_service.list_inspections(
        db,
        restroom_id=restroom_id,
        district=district,
        inspector=inspector,
        conformity=conformity,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[AccessibilityInspectionOut](
        items=[accessibility_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=AccessibilityInspectionOut, status_code=201, summary="登记无障碍检查")
def create_inspection(
    payload: AccessibilityInspectionCreate, db: Annotated[Session, Depends(get_db)]
) -> AccessibilityInspectionOut:
    """登记设施配置与完好状态，服务端按检查标准判定符合性；不符合项自动生成待整改事项。"""
    return accessibility_service.to_out(accessibility_service.create_inspection(db, payload))


@router.get("/summary", response_model=AccessibilitySummary, summary="无障碍达标率汇总")
def get_summary(db: Annotated[Session, Depends(get_db)]) -> AccessibilitySummary:
    """按区域与公厕汇总无障碍达标率（区域取各公厕最近一次检查达标率的平均）。"""
    return accessibility_service.build_summary(db)


@router.get("/{inspection_id}", response_model=AccessibilityInspectionOut, summary="无障碍检查详情")
def get_inspection(
    inspection_id: int, db: Annotated[Session, Depends(get_db)]
) -> AccessibilityInspectionOut:
    return accessibility_service.to_out(accessibility_service.get_inspection(db, inspection_id))


@router.patch("/{inspection_id}", response_model=AccessibilityInspectionOut, summary="更新无障碍检查")
def update_inspection(
    inspection_id: int,
    payload: AccessibilityInspectionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> AccessibilityInspectionOut:
    return accessibility_service.to_out(
        accessibility_service.update_inspection(db, inspection_id, payload)
    )


@router.delete("/{inspection_id}", response_model=MessageOut, summary="删除无障碍检查")
def delete_inspection(
    inspection_id: int, db: Annotated[Session, Depends(get_db)]
) -> MessageOut:
    accessibility_service.delete_inspection(db, inspection_id)
    return MessageOut(message="删除成功")
