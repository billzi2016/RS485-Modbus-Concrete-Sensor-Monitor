from __future__ import annotations

from typing import Literal

from app.services.local_mock import LocalMockProvider
from app.services.redis_reader import RedisReader

MetricName = Literal["strain", "temp", "freq", "max_strain"]


class DashboardService:
    """
    页面层统一数据入口。

    优先级：
    1. RedisReader：读取由 collector 或 mock_server --feed 写入的数据
    2. LocalMockProvider：Redis 不可用时降级，保证开发时页面可用
    """

    def __init__(self) -> None:
        self.redis_reader = RedisReader()
        self.local_provider = LocalMockProvider()

    def get_summary(self) -> dict[str, object]:
        try:
            return self.redis_reader.get_summary()
        except Exception:
            return self.local_provider.get_summary()

    def get_matrix(self, metric: MetricName) -> dict[str, object]:
        try:
            return self.redis_reader.get_matrix(metric)
        except Exception:
            return self.local_provider.get_matrix(metric)

    def get_history(self, gateway_ip: str, sensor_index: int, metric: MetricName) -> dict[str, object]:
        try:
            return self.redis_reader.get_history(gateway_ip, sensor_index, metric)
        except Exception:
            return self.local_provider.get_history(gateway_ip, sensor_index, metric)


dashboard_service = DashboardService()
