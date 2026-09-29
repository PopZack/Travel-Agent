"""Travel Agent — 配置加载。

复用 src/travel_agent/config.py 的 Settings，扩展 FastAPI/DB/Redis 配置。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM（火山方舟 / OpenAI 兼容接口）
    llm_base_url: str = Field(..., description="LLM API base URL")
    llm_api_key: str = Field(..., description="LLM API key")
    llm_model: str = Field(..., description="默认模型名")
    planner_model: str | None = None

    # Amadeus（可选）
    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    amadeus_env: Literal["test", "prod"] = "test"

    # Google Places
    google_places_api_key: str = Field(..., description="Google Places API key")

    # OpenWeather
    openweather_api_key: str = Field(..., description="OpenWeather API key")

    # 汇率（可选）
    exchange_rate_api_key: str | None = None

    # 高德地图（可选）
    amap_api_key: str | None = None

    # OSRM
    osrm_base_url: str = "http://router.project-osrm.org"

    # 应用
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # 数据库
    database_url: str = "sqlite:///./travel_agent.db"

    # Redis（可选，不配则用内存缓存）
    redis_url: str | None = None

    @model_validator(mode="after")
    def _warn_prod(self) -> "Settings":
        if self.amadeus_env == "prod":
            import warnings

            warnings.warn(
                "AMADEUS_ENV=prod：下单将真实出票并扣款，请确认已获生产授权。",
                stacklevel=2,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """单例配置。整个进程共享一份。"""
    return Settings()
