"""将指定用户设为超级管理员，或重置其密码。"""

from __future__ import annotations

import argparse
import getpass

from sqlalchemy.orm import Session

from .auth import hash_password, revoke_all_sessions
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


def reset_admin_password(db: Session, username: str) -> str:
    user = db.query(User).filter(User.display_name == username).first()
    if user is None:
        raise SystemExit(f"用户不存在：{username}")

    password = getpass.getpass("新密码：")
    if len(password) < 8:
        raise SystemExit("密码长度不能少于 8 位")
    if len(password) > 128:
        raise SystemExit("密码长度不能超过 128 位")
    confirmation = getpass.getpass("再次输入新密码：")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")

    user.password_hash = hash_password(password)
    revoke_all_sessions(db, user.id)
    db.commit()
    return user.display_name


def main() -> None:
    parser = argparse.ArgumentParser(description="管理端账号维护工具")
    parser.add_argument("--username", required=True, help="现有用户登录名")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="交互式重置该用户密码并强制下线全部会话",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_admin_data(db)
        if args.reset_password:
            username = reset_admin_password(db, args.username)
            print(f"已重置用户 {username} 的密码并强制下线全部会话")
        else:
            username = make_super_admin(db, args.username)
            print(f"已将用户 {username} 设为超级管理员")
    finally:
        db.close()


if __name__ == "__main__":
    main()
