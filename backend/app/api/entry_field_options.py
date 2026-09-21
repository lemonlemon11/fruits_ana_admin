"""录单字段字典维护接口，仅 fruit_admin 可访问。"""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_admin_user
from ..db import get_db
from ..models import EntryFieldOption, User
from ..schemas import (
    EntryFieldOptionCreate,
    EntryFieldOptionListResponse,
    EntryFieldOptionRead,
    EntryFieldOptionReorder,
    EntryFieldOptionUpdate,
)


router = APIRouter(prefix="/api/admin/entry-field-options", tags=["entry-field-options"])
VARIETY_PATTERN = re.compile(r"^(?:[A-F]|AB|BC)$")


def _require_option(db: Session, option_id: int) -> EntryFieldOption:
    option = db.get(EntryFieldOption, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="字段选项不存在")
    return option


def _validate_value(field_key: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="选项值不能为空")
    if field_key == "variety":
        if not VARIETY_PATTERN.fullmatch(value):
            raise HTTPException(
                status_code=422,
                detail="品种必须是 A-F，或组合等级 AB、BC",
            )
    return value


def _option_read(option: EntryFieldOption) -> EntryFieldOptionRead:
    return EntryFieldOptionRead.model_validate(option)


@router.get("", response_model=EntryFieldOptionListResponse)
def list_options(
    field: str = Query(default="market", pattern="^(market|variety)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    rows = (
        db.query(EntryFieldOption)
        .filter(EntryFieldOption.field_key == field)
        .order_by(
            EntryFieldOption.is_active.desc(),
            EntryFieldOption.sort_order,
            EntryFieldOption.id,
        )
        .all()
    )
    return {"items": [_option_read(row) for row in rows], "total": len(rows)}


@router.post("", response_model=EntryFieldOptionRead, status_code=201)
def create_option(
    payload: EntryFieldOptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    value = _validate_value(payload.field_key, payload.value)
    exists = (
        db.query(EntryFieldOption)
        .filter(
            EntryFieldOption.field_key == payload.field_key,
            EntryFieldOption.value == value,
        )
        .first()
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="该字段选项已存在")
    option = EntryFieldOption(
        field_key=payload.field_key,
        value=value,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(option)
    try:
        db.flush()
        record_operation_log(
            db,
            request,
            current_user,
            "entry-field",
            "create",
            target_type="entry_field_option",
            target_id=str(option.id),
            summary=f"新增录单字段 {payload.field_key}={value}",
            after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该字段选项已存在") from None
    return _option_read(option)


@router.patch("/{option_id}", response_model=EntryFieldOptionRead)
def update_option(
    option_id: int,
    payload: EntryFieldOptionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    option = _require_option(db, option_id)
    before = _option_read(option).model_dump(mode="json")
    if payload.value is not None:
        value = _validate_value(option.field_key, payload.value)
        exists = (
            db.query(EntryFieldOption)
            .filter(
                EntryFieldOption.field_key == option.field_key,
                EntryFieldOption.value == value,
                EntryFieldOption.id != option.id,
            )
            .first()
        )
        if exists is not None:
            raise HTTPException(status_code=409, detail="该字段选项已存在")
        option.value = value
    if payload.sort_order is not None:
        option.sort_order = payload.sort_order
    if payload.is_active is not None:
        option.is_active = payload.is_active
    record_operation_log(
        db,
        request,
        current_user,
        "entry-field",
        "update",
        target_type="entry_field_option",
        target_id=str(option.id),
        summary=f"更新录单字段 {option.field_key}={option.value}",
        before_data=json.dumps(before, ensure_ascii=False),
        after_data=json.dumps(_option_read(option).model_dump(mode="json"), ensure_ascii=False),
    )
    db.commit()
    return _option_read(option)


@router.put("/reorder", response_model=EntryFieldOptionListResponse)
def reorder_options(
    payload: EntryFieldOptionReorder,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """按提交顺序批量更新同一字段下的排序值。"""

    options = (
        db.query(EntryFieldOption)
        .filter(
            EntryFieldOption.field_key == payload.field_key,
            EntryFieldOption.id.in_(payload.item_ids),
        )
        .all()
    )
    by_id = {option.id: option for option in options}
    if len(by_id) != len(payload.item_ids) or len(by_id) != len(set(payload.item_ids)):
        db.rollback()
        raise HTTPException(status_code=422, detail="排序项包含无效或重复的选项")

    for index, option_id in enumerate(payload.item_ids):
        by_id[option_id].sort_order = index

    record_operation_log(
        db,
        request,
        current_user,
        "entry-field",
        "reorder",
        target_type="entry_field_option",
        target_id=payload.field_key,
        summary=f"调整录单字段排序 {payload.field_key}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()

    rows = (
        db.query(EntryFieldOption)
        .filter(EntryFieldOption.field_key == payload.field_key)
        .order_by(EntryFieldOption.sort_order, EntryFieldOption.id)
        .all()
    )
    return {"items": [_option_read(row) for row in rows], "total": len(rows)}


@router.delete("/{option_id}", status_code=204)
def delete_option(
    option_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    option = _require_option(db, option_id)
    record_operation_log(
        db,
        request,
        current_user,
        "entry-field",
        "delete",
        target_type="entry_field_option",
        target_id=str(option.id),
        summary=f"删除录单字段 {option.field_key}={option.value}",
    )
    db.delete(option)
    db.commit()
    return None


__all__ = ["router"]
