"""数据库引擎、会话与初始化。"""

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _prepare_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    path = url.replace("sqlite:///", "", 1)
    if path.startswith(":memory:"):
        return
    directory = Path(path).parent
    if str(directory) not in ("", "."):
        os.makedirs(directory, exist_ok=True)


_prepare_sqlite_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args(settings.database_url),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _apply_lightweight_migrations() -> None:
    """为存量 SQLite 库补充新增列（create_all 不会修改已存在的表）。"""
    if not settings.database_url.startswith("sqlite"):
        return
    new_columns = {
        "issues": ["accessibility_inspection_id"],
    }
    with engine.begin() as conn:
        for table, columns in new_columns.items():
            existing = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            if not existing:
                continue  # 表尚未创建，交给 create_all
            for column in columns:
                if column not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER")


def init_db() -> None:
    from app import models  # noqa: F401  确保模型完成注册

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
