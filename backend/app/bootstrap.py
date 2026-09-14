"""将一个已有用户设为超级管理员。"""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import AdminAccess, User
from .seed import seed_admin_data


def make_super_admin(db: Session, username: str) -> str:
    user = db.query(User).filter(User.display_name == username).first()
    if user is None:
        raise SystemExit(f"用户不存在：{username}")

    access = db.query(AdminAccess).filter(AdminAccess.user_id == user.id).first()
    if access is None:
        access = AdminAccess(user_id=user.id, is_active=True, is_super_admin=True)
        db.add(access)
    else:
        access.is_active = True
        access.is_super_admin = True
    db.commit()
    return user.display_name


def main() -> None:
    parser = argparse.ArgumentParser(description="将已有用户设为超级管理员")
    parser.add_argument("--username", required=True, help="现有用户登录名")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_admin_data(db)
        username = make_super_admin(db, args.username)
        print(f"已将用户 {username} 设为超级管理员")
    finally:
        db.close()


if __name__ == "__main__":
    main()
