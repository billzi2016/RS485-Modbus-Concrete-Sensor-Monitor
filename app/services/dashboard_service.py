from __future__ import annotations

from typing import Literal

from app.services.local_mock import LocalMockProvider
from app.services.redis_reader import KEY_PREFIX_REAL, KEY_PREFIX_TEST, RedisReader

MetricName = Literal["strain", "temp", "freq", "max_strain"]

# source 取值：
#   "real"    → 读 monitor:sensor:* （真实 collector 写入）
#   "fastapi" → 读 monitor:test:*   （mock_server --feed 写入）
#   "mock"    → LocalMockProvider，不碰 Redis


class DashboardService:
    def __init__(self) -> None:
        self.redis_reader = RedisReader()
        self.local_provider = LocalMockProvider()

    def _key_prefix(self, source: str) -> str:
        return KEY_PREFIX_TEST if source == "fastapi" else KEY_PREFIX_REAL

    def get_summary(self, source: str = "real") -> dict[str, object]:
        if source == "mock":
            return self.local_provider.get_summary()
        try:
            return self.redis_reader.get_summary(key_prefix=self._key_prefix(source))
        except Exception:
            return self.local_provider.get_summary()

    def get_matrix(self, metric: MetricName, source: str = "real") -> dict[str, object]:
        if source == "mock":
            return self.local_provider.get_matrix(metric)
        try:
            return self.redis_reader.get_matrix(metric, key_prefix=self._key_prefix(source))
        except Exception:
            return self.local_provider.get_matrix(metric)

    def get_history(self, gateway_ip: str, sensor_index: int, metric: MetricName) -> dict[str, object]:
        try:
            return self.redis_reader.get_history(gateway_ip, sensor_index, metric)
        except Exception:
            return self.local_provider.get_history(gateway_ip, sensor_index, metric)


dashboard_service = DashboardService()
