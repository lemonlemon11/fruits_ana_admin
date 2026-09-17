"""字段转换规则维护接口，仅 fruit_admin 可访问。"""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_fruit_admin
from ..db import get_db
from ..models import FieldConversionRule, User
from ..schemas import (
    FieldConversionRuleCreate,
    FieldConversionRuleListResponse,
    FieldConversionRuleRead,
    FieldConversionRuleReorder,
    FieldConversionRuleUpdate,
)


router = APIRouter(prefix="/api/admin/field-conversion-rules", tags=["field-conversion-rules"])
VALUE_PATTERN = re.compile(r"^[A-Z]{1,4}$")


def _require_rule(db: Session, rule_id: int) -> FieldConversionRule:
    rule = db.get(FieldConversionRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="转换规则不存在")
    return rule


def _validate_value(label: str, value: str) -> str:
    value = value.strip().upper()
    if not VALUE_PATTERN.fullmatch(value):
        raise HTTPException(status_code=422, detail=f"{label}必须由 1-4 个大写英文字母组成")
    return value


def _rule_read(rule: FieldConversionRule) -> FieldConversionRuleRead:
    return FieldConversionRuleRead.model_validate(rule)


@router.get("", response_model=FieldConversionRuleListResponse)
def list_rules(
    field: str = Query(default="grade", pattern=r"^(grade)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_fruit_admin),
):
    rows = (
        db.query(FieldConversionRule)
        .filter(FieldConversionRule.field_key == field)
        .order_by(
            FieldConversionRule.is_active.desc(),
            FieldConversionRule.sort_order,
            FieldConversionRule.id,
        )
        .all()
    )
    return {"items": [_rule_read(row) for row in rows], "total": len(rows)}


@router.post("", response_model=FieldConversionRuleRead, status_code=201)
def create_rule(
    payload: FieldConversionRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_fruit_admin),
):
    source_value = _validate_value("原始值", payload.source_value)
    target_value = _validate_value("目标值", payload.target_value)
    exists = (
        db.query(FieldConversionRule)
        .filter(
            FieldConversionRule.field_key == payload.field_key,
            FieldConversionRule.source_value == source_value,
        )
        .first()
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="该原始值的转换规则已存在")
    rule = FieldConversionRule(
        field_key=payload.field_key,
        source_value=source_value,
        target_value=target_value,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        description=payload.description,
    )
    db.add(rule)
    try:
        db.flush()
        record_operation_log(
            db,
            request,
            current_user,
            "field-conversion",
            "create",
            target_type="field_conversion_rule",
            target_id=str(rule.id),
            summary=f"新增转换规则 {payload.field_key}:{source_value}→{target_value}",
            after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该原始值的转换规则已存在") from None
    return _rule_read(rule)


@router.patch("/{rule_id}", response_model=FieldConversionRuleRead)
def update_rule(
    rule_id: int,
    payload: FieldConversionRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_fruit_admin),
):
    rule = _require_rule(db, rule_id)
    before = _rule_read(rule).model_dump(mode="json")
    if payload.source_value is not None:
        source_value = _validate_value("原始值", payload.source_value)
        exists = (
            db.query(FieldConversionRule)
            .filter(
                FieldConversionRule.field_key == rule.field_key,
                FieldConversionRule.source_value == source_value,
                FieldConversionRule.id != rule.id,
            )
            .first()
        )
        if exists is not None:
            raise HTTPException(status_code=409, detail="该原始值的转换规则已存在")
        rule.source_value = source_value
    if payload.target_value is not None:
        rule.target_value = _validate_value("目标值", payload.target_value)
    if payload.sort_order is not None:
        rule.sort_order = payload.sort_order
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    if payload.description is not None:
        rule.description = payload.description
    record_operation_log(
        db,
        request,
        current_user,
        "field-conversion",
        "update",
        target_type="field_conversion_rule",
        target_id=str(rule.id),
        summary=f"更新转换规则 {rule.field_key}:{rule.source_value}→{rule.target_value}",
        before_data=json.dumps(before, ensure_ascii=False),
        after_data=json.dumps(_rule_read(rule).model_dump(mode="json"), ensure_ascii=False),
    )
    db.commit()
    return _rule_read(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_fruit_admin),
):
    rule = _require_rule(db, rule_id)
    record_operation_log(
        db,
        request,
        current_user,
        "field-conversion",
        "delete",
        target_type="field_conversion_rule",
        target_id=str(rule.id),
        summary=f"删除转换规则 {rule.field_key}:{rule.source_value}→{rule.target_value}",
        before_data=json.dumps(_rule_read(rule).model_dump(mode="json"), ensure_ascii=False),
    )
    db.delete(rule)
    db.commit()


@router.put("/reorder", response_model=FieldConversionRuleListResponse)
def reorder_rules(
    payload: FieldConversionRuleReorder,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_fruit_admin),
):
    rows = {
        rule.id: rule
        for rule in db.query(FieldConversionRule)
        .filter(FieldConversionRule.field_key == payload.field_key)
        .all()
    }
    if set(payload.item_ids) != set(rows):
        raise HTTPException(status_code=422, detail="排序项与当前规则不一致")
    for order, rule_id in enumerate(payload.item_ids):
        rows[rule_id].sort_order = order
    record_operation_log(
        db,
        request,
        current_user,
        "field-conversion",
        "reorder",
        target_type="field_conversion_rule",
        summary=f"调整转换规则顺序 {payload.item_ids}",
    )
    db.commit()
    ordered = sorted(rows.values(), key=lambda rule: (not rule.is_active, rule.sort_order, rule.id))
    return {"items": [_rule_read(rule) for rule in ordered], "total": len(ordered)}
