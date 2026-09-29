"""日志初始化。

从 Settings.log_level 读取级别，配置 root logger。
"""

from __future__ import annotations

import logging

from app.common.config import get_settings


def setup_logging() -> None:
    """初始化日志，使 LOG_LEVEL 配置生效。"""
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
