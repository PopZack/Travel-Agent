"""配置加载：从环境变量/.env 读取所有 API key 与运行参数。

启动时调用 ``Settings()`` 即可；缺失必需 key 会抛出带可读提示的 ValidationError。
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
    llm_base_url: str = Field(..., description="LLM API base URL，如火山方舟 endpoint")
    llm_api_key: str = Field(..., description="LLM API key")
    llm_model: str = Field(..., description="默认模型名，如 deepseek-v4-flash")
    # 可选：规划节点用更强模型；不填则统一用 llm_model
    planner_model: str | None = None

    # Amadeus（可选：无 key 时跳过机酒搜索与预订，行程规划仍可用）
    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    amadeus_env: Literal["test", "prod"] = Field(
        default="test", description="test 只搜索不真扣款，prod 真实出票"
    )

    # Google Places
    google_places_api_key: str = Field(..., description="Google Places API key")

    # OpenWeather
    openweather_api_key: str = Field(..., description="OpenWeather API key")

    # 汇率（可选）
    exchange_rate_api_key: str | None = None

    # 高德地图（可选：景点/路线/天气，国内数据好）
    amap_api_key: str | None = None

    # OSRM
    osrm_base_url: str = "http://router.project-osrm.org"

    # 应用
    streamlit_server_port: int = 8501
    log_level: str = "INFO"

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
