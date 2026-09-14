"""管理端系统配置接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_permission
from ..db import get_db
from ..models import AdminSetting, User
from ..schemas import SettingUpdate


router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])

DEFAULT_SETTINGS = {
    "public_register": ("true", "是否允许果农端公开注册"),
    "session_days": ("7", "普通会话默认有效天数"),
    "remember_days": ("30", "记住登录会话有效天数"),
    "password_min_length": ("8", "密码最小长度"),
}


def _seed_settings(db: Session) -> None:
    for key, (value, description) in DEFAULT_SETTINGS.items():
        item = db.query(AdminSetting).filter(AdminSetting.key == key).first()
        if item is None:
            db.add(AdminSetting(key=key, value=value, description=description))
    db.commit()


@router.get("")
def list_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:config:view")),
):
    _seed_settings(db)
    items = db.query(AdminSetting).order_by(AdminSetting.key).all()
    return {
        "items": [
            {
                "key": item.key,
                "value": item.value,
                "description": item.description,
            }
            for item in items
        ]
    }


@router.patch("/{key}")
def update_setting(
    key: str,
    payload: SettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:config:update")),
):
    item = db.query(AdminSetting).filter(AdminSetting.key == key).first()
    if item is None:
        raise HTTPException(status_code=404, detail="配置项不存在")
    if payload.value is not None:
        item.value = payload.value
    if payload.description is not None:
        item.description = payload.description
    record_operation_log(
        db,
        request,
        current_user,
        "config",
        "update",
        target_type="setting",
        target_id=key,
        summary=f"修改系统配置 {key}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()
    return {"key": item.key, "value": item.value, "description": item.description}
