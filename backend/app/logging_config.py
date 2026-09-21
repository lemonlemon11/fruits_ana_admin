"""管理端统一日志配置：控制台、轮转文件与请求 ID 注入。"""

from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = BACKEND_DIR / "data" / "logs"
DEFAULT_LOG_FILE = "fruits_ana_admin.log"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """把当前请求 ID 注入日志记录，供 Formatter 使用。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _level_from_env(default: str = "INFO") -> int:
    name = os.getenv("FRUIT_ADMIN_LOG_LEVEL", default).strip().upper()
    return getattr(logging, name, logging.INFO)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_logger(name: str = "fruits_ana_admin") -> logging.Logger:
    """返回管理端统一命名空间下的日志器。"""

    return logging.getLogger(name)


def configure_logging() -> None:
    """配置管理端日志；重复调用时保持幂等。"""

    logger = logging.getLogger("fruits_ana_admin")
    if logger.handlers:
        return

    logger.setLevel(_level_from_env())
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(RequestIdFilter())
    logger.addHandler(console)

    log_dir = Path(os.getenv("FRUIT_ADMIN_LOG_DIR", str(DEFAULT_LOG_DIR)))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / os.getenv("FRUIT_ADMIN_LOG_FILE", DEFAULT_LOG_FILE)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=_int_env("FRUIT_ADMIN_LOG_MAX_BYTES", 5 * 1024 * 1024),
        backupCount=_int_env("FRUIT_ADMIN_LOG_BACKUP_COUNT", 5),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIdFilter())
    logger.addHandler(file_handler)


__all__ = [
    "RequestIdFilter",
    "configure_logging",
    "get_logger",
    "request_id_var",
]
