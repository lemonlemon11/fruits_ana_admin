"""管理端系统配置接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_admin_user
from ..db import get_db
from ..models import AdminSetting, User
from ..schemas import SettingUpdate


router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])

DEFAULT_SETTINGS = {
    "public_register": {
        "value": "true",
        "description": "是否允许果农端公开注册（由用户端维护，管理端只读）",
        "editable": False,
    },
    "session_days": {
        "value": "7",
        "description": "普通会话默认有效天数",
        "editable": True,
    },
    "remember_days": {
        "value": "30",
        "description": "记住登录会话有效天数",
        "editable": True,
    },
    "password_min_length": {
        "value": "8",
        "description": "密码最小长度",
        "editable": True,
    },
}


def _setting_meta(key: str) -> dict:
    return DEFAULT_SETTINGS.get(key, {"editable": True})


def _seed_settings(db: Session) -> None:
    for key, meta in DEFAULT_SETTINGS.items():
        item = db.query(AdminSetting).filter(AdminSetting.key == key).first()
        if item is None:
            db.add(
                AdminSetting(
                    key=key,
                    value=meta["value"],
                    description=meta["description"],
                )
            )
    db.commit()


@router.get("")
def list_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    _seed_settings(db)
    items = db.query(AdminSetting).order_by(AdminSetting.key).all()
    return {
        "items": [
            {
                "key": item.key,
                "value": item.value,
                "description": item.description,
                "editable": _setting_meta(item.key).get("editable", True),
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
    current_user: User = Depends(require_admin_user),
):
    item = db.query(AdminSetting).filter(AdminSetting.key == key).first()
    if item is None:
        raise HTTPException(status_code=404, detail="配置项不存在")
    if not _setting_meta(key).get("editable", True):
        raise HTTPException(status_code=400, detail="该配置由用户端管理，管理端不可修改")
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
    return {
        "key": item.key,
        "value": item.value,
        "description": item.description,
        "editable": True,
    }
