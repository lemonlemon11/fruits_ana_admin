"""管理员端 FastAPI 应用入口。"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder as _orig_jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
import fastapi.routing as _routing

from .logging_config import configure_logging, get_logger, request_id_var


_BEIJING_TZ = ZoneInfo("Asia/Shanghai")

configure_logging()
logger = get_logger()


def _beijing_encoder(obj, *args, **kwargs):
    if isinstance(obj, datetime) and obj.tzinfo is not None:
        return obj.astimezone(_BEIJING_TZ).isoformat()
    return _orig_jsonable_encoder(obj, *args, **kwargs)


# Patch both references to ensure serialization uses Beijing timezone
import fastapi.encoders
fastapi.encoders.jsonable_encoder = _beijing_encoder
_routing.jsonable_encoder = _beijing_encoder

from .api.auth import router as auth_router
from .api.dashboard import router as dashboard_router
from .api.data import router as data_router
from .api.entry_field_options import router as entry_field_options_router
from .api.field_conversion_rules import router as field_conversion_rules_router
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
app.include_router(entry_field_options_router)
app.include_router(field_conversion_rules_router)
app.include_router(roles_router)
app.include_router(menus_router)
app.include_router(permissions_router)
app.include_router(notifications_router)
app.include_router(data_router)
app.include_router(logs_router)
app.include_router(settings_router)


@app.middleware("http")
async def log_requests(request, call_next):
    """记录每个请求的耗时、状态码与请求 ID；未捕获异常落 error 日志。"""

    request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        _log_request(request.method, request.url.path, response.status_code, duration_ms)
        return response
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "request failed method=%s path=%s status=500 duration_ms=%.1f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    finally:
        request_id_var.reset(token)


def _log_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    if status_code >= 500:
        logger.error(
            "request completed method=%s path=%s status=%s duration_ms=%.1f",
            method,
            path,
            status_code,
            duration_ms,
        )
    elif status_code >= 400:
        logger.warning(
            "request completed method=%s path=%s status=%s duration_ms=%.1f",
            method,
            path,
            status_code,
            duration_ms,
        )
    else:
        logger.info(
            "request completed method=%s path=%s status=%s duration_ms=%.1f",
            method,
            path,
            status_code,
            duration_ms,
        )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fruits-ana-admin"}
