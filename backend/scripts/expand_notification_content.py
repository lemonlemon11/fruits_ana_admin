"""将 ``admin_notification.content`` 从 TEXT 扩为 MEDIUMTEXT。

富文本通知允许插入 Base64 图片，MySQL ``TEXT`` 上限约 64KB，容易截断或报错。
模型已按 MySQL ``MEDIUMTEXT`` 生成新表；本脚本只负责升级既有 MySQL 表。
默认演练，``--apply`` 才写库；非 MySQL 跳过。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import engine  # noqa: E402


TABLE = "admin_notification"
COLUMN = "content"


def quote(identifier: str) -> str:
    return f"`{identifier}`"


def needs_migration() -> bool:
    if engine.dialect.name != "mysql":
        return False
    inspector = inspect(engine)
    if TABLE not in inspector.get_table_names():
        return False
    for column in inspector.get_columns(TABLE):
        if column.get("name") != COLUMN:
            continue
        column_type = str(column.get("type") or "").upper()
        return "MEDIUMTEXT" not in column_type
    return False


def migrate(*, apply: bool = False) -> str | None:
    if engine.dialect.name != "mysql":
        print("[跳过] 仅 MySQL 需要执行本迁移。")
        return None
    if not needs_migration():
        print("[跳过] admin_notification.content 已是 MEDIUMTEXT 或表不存在。")
        return None
    statement = (
        f"ALTER TABLE {quote(TABLE)} MODIFY COLUMN {quote(COLUMN)} MEDIUMTEXT NOT NULL"
    )
    if not apply:
        print(f"[演练] {statement}")
        return None
    with engine.begin() as connection:
        connection.execute(text(statement))
    print(f"[已执行] {statement}")
    return statement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="真正写入数据库；默认只演练")
    args = parser.parse_args(argv)
    migrate(apply=args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
