"""管理员端 FastAPI 应用入口。"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.dashboard import router as dashboard_router
from .api.data import router as data_router
from .api.logs import router as logs_router
from .api.menus import router as menus_router
from .api.notifications import router as notifications_router
from .api.permissions import router as permissions_router
from .api.roles import router as roles_router
from .api.settings import router as settings_router
from .api.users import router as users_router
from .db import SessionLocal, init_db
from .seed import seed_admin_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_admin_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="SLD 水果市场销售分析 · 管理员端",
    version="0.1.0",
    lifespan=lifespan,
)

origins = [
    item.strip()
    for item in os.getenv(
        "FRUIT_ADMIN_CORS_ORIGINS",
        "http://127.0.0.1:54000,http://localhost:54000",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(menus_router)
app.include_router(permissions_router)
app.include_router(notifications_router)
app.include_router(data_router)
app.include_router(logs_router)
app.include_router(settings_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fruits-ana-admin"}
