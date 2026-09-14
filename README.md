# SLD 水果市场销售分析 · 管理员端

独立于 `fruits_ana` 的管理端项目，复用同一个 MySQL 数据库，负责用户、角色、菜单、
权限、业务数据、审计日志和站内通知管理。

## 技术栈

- Backend：FastAPI + SQLAlchemy 2.0 + PyMySQL
- Frontend：Vue 3 + Vue Router + Vite
- Database：复用 `fruits_ana` 的 MySQL 数据库

## 目录

```text
fruits_ana_admin/
├── backend/   # 管理端 API
└── frontend/  # 管理端 SPA
```

## 配置

后端通过环境变量或 `backend/.env` 读取数据库配置：

```bash
cp backend/.env.example backend/.env
# 修改 backend/.env 中的数据库连接
```

## 初始化管理员角色与权限

后端启动时会自动创建 `admin_*` 表并写入默认菜单、权限和角色。

站内通知使用共享数据库中的 `admin_notification` 与
`admin_notification_recipient` 两张表。管理端负责创建、定时发布和阅读统计，
`fruits_ana` 用户端通过 `/api/notifications` 只读拉取并标记已读。

首次使用需将某个现有用户设为超级管理员：

```bash
.venv/bin/python -m app.bootstrap --username lhp
```

执行前请确认用户名存在。该命令只会创建角色绑定，不会创建新用户或修改密码。

## 启动

后端：

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

前端：

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0 --port 54000
```

访问 `http://127.0.0.1:54000`，登录后使用管理端。

## 验证

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## 安全说明

- 不提交 `backend/.env`；
- 不把数据库密码写入源码；
- 管理员权限以后端接口校验为准。
