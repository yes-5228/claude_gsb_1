"""无障碍设施专项检查模型。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AccessibilityResult
from app.core.database import Base


class AccessibilityCheck(Base):
    """一次无障碍设施专项检查，登记扶手、坡道、盲道、专用间的配置与完好状态。"""

    __tablename__ = "accessibility_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    inspector: Mapped[str] = mapped_column(String(60), index=True, comment="检查人")
    check_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="检查时间"
    )
    items: Mapped[list[dict]] = mapped_column(
        JSON, default=list, comment="设施登记明细（配置情况/完好状态/判定）"
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0, comment="检查项数")
    compliant_count: Mapped[int] = mapped_column(Integer, default=0, comment="符合项数")
    partial_count: Mapped[int] = mapped_column(Integer, default=0, comment="部分符合项数")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, comment="不符合项数")
    score: Mapped[float] = mapped_column(Float, default=0.0, comment="达标率（百分制）")
    result: Mapped[str] = mapped_column(
        String(20), default=AccessibilityResult.PASS.value, index=True, comment="检查结论"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="检查备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    restroom: Mapped["Restroom"] = relationship(back_populates="accessibility_checks")  # noqa: F821
    issues: Mapped[list["Issue"]] = relationship(back_populates="accessibility_check")  # noqa: F821
