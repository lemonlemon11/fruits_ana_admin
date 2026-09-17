# 录单字段配置 Implementation Plan（fruits_ana_admin）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在管理端新增录单字段配置页，由 `fruit_admin` 角色维护市场和品种下拉字典。

**Architecture:** 管理端复用 `fruits_ana` 同一 MySQL；新增共享表 `entry_field_option`；
新增 `/api/admin/entry-field-options`，后端用业务角色 `fruit_admin` 鉴权；
前端新增 `/admin/entry-fields` 页面并只对 `fruit_admin` 显示导航。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + MySQL；Vue 3 + Vue Router + Vite。

---

## File Structure

**Modify:**
- `backend/app/models.py`
- `backend/app/auth.py`
- `backend/app/schemas.py`
- `backend/app/main.py`
- `backend/app/seed.py`
- `frontend/src/main.ts`
- `frontend/src/components/AdminLayout.vue`
- `frontend/src/types.ts`

**Create:**
- `backend/app/api/entry_field_options.py`
- `frontend/src/views/EntryFieldConfigView.vue`

---

## Task 1: 管理端共享表模型

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: 新增 `EntryFieldOption` 模型**

```python
class EntryFieldOption(Base):
    __tablename__ = "entry_field_option"
    __table_args__ = (
        Index("ux_entry_field_option", "field_key", "value", unique=True),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_key: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(PRECISE_DATETIME, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False)
```

- [ ] **Step 2: 运行编译检查**

```bash
.venv/bin/python -m py_compile backend/app/models.py
```

---

## Task 2: `fruit_admin` 鉴权

**Files:**
- Modify: `backend/app/auth.py`

- [ ] **Step 1: 新增 `require_fruit_admin` 依赖**

检查当前用户业务角色中是否包含 `fruit_admin`：

```python
def require_fruit_admin(
    request: Request,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> User:
    roles = get_roles_for_user(db, current_user.id)
    if not any(role.code == "fruit_admin" and role.is_active for role in roles):
        raise HTTPException(status_code=403, detail="仅水果系统管理员可配置录单字段")
    return current_user
```

- [ ] **Step 2: 编译检查**

```bash
.venv/bin/python -m py_compile backend/app/auth.py
```

---

## Task 3: 字段配置 API

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/api/entry_field_options.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 新增 DTO**

`EntryFieldOptionCreate`、`EntryFieldOptionUpdate`、`EntryFieldOptionRead`。

- [ ] **Step 2: 实现列表接口**

`GET /api/admin/entry-field-options?field=market|variety`，返回启用项在前、按 `sort_order` 排序。

- [ ] **Step 3: 实现新增接口**

`POST /api/admin/entry-field-options`

- `field_key` 只允许 `market` / `variety`。
- `variety` 值必须匹配 `^[A-Z]$`，且不允许 `BC`。
- 同 `field_key + value` 冲突返回 409。

- [ ] **Step 4: 实现编辑和删除接口**

- `PATCH /api/admin/entry-field-options/{option_id}`：更新值、排序、启用状态。
- `DELETE /api/admin/entry-field-options/{option_id}`：删除前确认未被录单引用；当前设计暂存值副本，因此可直接删除并返回 204。

- [ ] **Step 5: 注册路由**

- [ ] **Step 6: 接口冒烟**

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

---

## Task 4: 初始字典与业务权限种子

**Files:**
- Modify: `backend/app/seed.py`

- [ ] **Step 1: 扩展业务权限**

在 `FRUIT_PERMISSIONS` 增加：

```python
("entry:view", "查看录单", "entry", "menu"),
("entry:create", "新增录单", "entry", "action"),
("entry:update", "修改手工录单", "entry", "action"),
("entry:export", "导出手工录单", "entry", "action"),
```

- [ ] **Step 2: 扩展业务菜单**

增加录单菜单，`route_path=/entry`，`component=EntryView`，`permission_code=entry:view`。

- [ ] **Step 3: 更新角色授权**

- `fruit_admin`：全部录单权限。
- `operator`：全部录单权限。
- `data_entry`：全部录单权限。
- `viewer`：不授权。

- [ ] **Step 4: 预置 `variety` A-F**

幂等创建 `A`、`B`、`C`、`D`、`E`、`F`。

- [ ] **Step 5: 启动验证种子写入**

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

---

## Task 5: 管理端前端页面

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/components/AdminLayout.vue`
- Create: `frontend/src/views/EntryFieldConfigView.vue`

- [ ] **Step 1: 增加类型与 API 方法**

- `EntryFieldOption`。
- `getEntryFieldOptions`、`createEntryFieldOption`、`updateEntryFieldOption`、`deleteEntryFieldOption`。

- [ ] **Step 2: 新增路由**

`/admin/entry-fields`，`meta: { requiresAuth: true, fruitAdminOnly: true, title: '录单字段配置' }`。

- [ ] **Step 3: 路由守卫增加 `fruitAdminOnly`**

检查 `currentUser.roles` 是否包含 `fruit_admin`。

- [ ] **Step 4: 导航显示**

只有 `fruit_admin` 角色显示“录单字段配置”。

- [ ] **Step 5: 实现页面**

- 两个 Tab：市场 / 品种。
- 列表展示值、排序、启用状态。
- 新增/编辑/删除/停用。
- 品种只允许单个大写字母，提示后续可在配置中扩展。

- [ ] **Step 6: 验证**

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

---

## Task 6: 文档与总验证

- [ ] 更新 `README.md`
- [ ] 更新 `docs/管理端实施说明.md`
- [ ] 运行管理端构建与接口冒烟

```bash
.venv/bin/python -m py_compile $(find backend/app -name '*.py')
npm --prefix frontend run typecheck
npm --prefix frontend run build
```
