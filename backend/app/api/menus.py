"""管理端菜单管理接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_admin_user
from ..db import get_db
from ..models import AdminMenu, AdminRoleMenu, User
from ..schemas import MenuCreate, MenuUpdate
from ..serializers import menu_read, menu_tree


router = APIRouter(prefix="/api/admin/menus", tags=["admin-menus"])


def _require_menu(db: Session, menu_id: int) -> AdminMenu:
    menu = db.get(AdminMenu, menu_id)
    if menu is None:
        raise HTTPException(status_code=404, detail="菜单不存在")
    return menu


@router.get("/tree")
def menu_tree_view(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    menus = db.query(AdminMenu).order_by(AdminMenu.sort_order, AdminMenu.id).all()
    return {"items": menu_tree(menus)}


@router.get("")
def list_menus(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    menus = db.query(AdminMenu).order_by(AdminMenu.sort_order, AdminMenu.id).all()
    return {"items": [menu_read(menu) for menu in menus], "total": len(menus)}


@router.post("", status_code=201)
def create_menu(
    payload: MenuCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    if payload.parent_id is not None:
        _require_menu(db, payload.parent_id)

    menu = AdminMenu(**payload.model_dump())
    db.add(menu)
    db.flush()
    record_operation_log(
        db,
        request,
        current_user,
        "menu",
        "create",
        target_type="menu",
        target_id=str(menu.id),
        summary=f"创建菜单 {menu.name}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()
    return menu_read(menu)


@router.patch("/{menu_id}")
def update_menu(
    menu_id: int,
    payload: MenuUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    menu = _require_menu(db, menu_id)
    before = json.dumps(menu_read(menu), ensure_ascii=False, default=str)
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] == menu_id:
        raise HTTPException(status_code=400, detail="父级菜单不能是自身")
    if data.get("parent_id") is not None:
        _require_menu(db, data["parent_id"])
    for key, value in data.items():
        setattr(menu, key, value)
    record_operation_log(
        db,
        request,
        current_user,
        "menu",
        "update",
        target_type="menu",
        target_id=str(menu.id),
        summary=f"更新菜单 {menu.name}",
        before_data=before,
        after_data=json.dumps(menu_read(menu), ensure_ascii=False, default=str),
    )
    db.commit()
    return menu_read(menu)


@router.delete("/{menu_id}", status_code=204)
def delete_menu(
    menu_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    menu = _require_menu(db, menu_id)
    children = db.query(AdminMenu).filter(AdminMenu.parent_id == menu_id).count()
    if children:
        raise HTTPException(status_code=400, detail="请先删除子菜单")
    references = db.query(AdminRoleMenu).filter(AdminRoleMenu.menu_id == menu_id).count()
    if references:
        raise HTTPException(status_code=400, detail="菜单已被角色引用，不能删除")

    record_operation_log(
        db,
        request,
        current_user,
        "menu",
        "delete",
        target_type="menu",
        target_id=str(menu.id),
        summary=f"删除菜单 {menu.name}",
    )
    db.delete(menu)
    db.commit()
    return None
