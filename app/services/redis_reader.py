from __future__ import annotations

import json
from typing import Literal

MetricName = Literal["strain", "temp", "freq", "max_strain"]

METRIC_RANGES: dict[MetricName, tuple[float, float]] = {
    "strain": (-5000.0, 5000.0),
    "temp": (-10.0, 40.0),
    "freq": (1000.0, 3000.0),
    "max_strain": (-10000.0, 10000.0),
}

KEY_PREFIX_REAL = "monitor:sensor"   # 真实 collector 写入
KEY_PREFIX_TEST = "monitor:test"     # mock_server --feed 写入


class RedisReader:
    """从 Redis 读取由 collector 或 mock_server --feed 写入的传感器数据。"""

    def __init__(self) -> None:
        self._client = None

    def _client_(self):
        if self._client is None:
            import redis
            from django.conf import settings
            self._client = redis.Redis.from_url(
                getattr(settings, "MONITOR_REDIS_URL", "redis://localhost:6379"),
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        return self._client

    def _sensor_key(self, gateway_ip: str, sensor_index: int, key_prefix: str = KEY_PREFIX_REAL) -> str:
        return f"{key_prefix}:{gateway_ip}:{sensor_index}"

    def _gateways(self) -> list[str]:
        from django.conf import settings
        return [f"10.54.79.{201 + i}" for i in range(settings.MONITOR_GATEWAY_COUNT)]

    def get_summary(self, key_prefix: str = KEY_PREFIX_REAL) -> dict[str, object]:
        from django.conf import settings
        client = self._client_()
        online_gateways = 0
        error_sensors = 0
        last_ts = 0

        for gateway_ip in self._gateways():
            gateway_online = False
            for sensor_index in range(1, settings.MONITOR_SENSOR_COUNT + 1):
                raw = client.get(self._sensor_key(gateway_ip, sensor_index, key_prefix))
                if raw:
                    snap = json.loads(raw)
                    if snap.get("online"):
                        gateway_online = True
                    if snap.get("display") == "Err":
                        error_sensors += 1
                    last_ts = max(last_ts, snap.get("ts", 0))
            if gateway_online:
                online_gateways += 1

        source_label = "redis" if key_prefix == KEY_PREFIX_REAL else "fastapi"
        return {
            "gateway_total": settings.MONITOR_GATEWAY_COUNT,
            "gateway_online": online_gateways,
            "gateway_offline": settings.MONITOR_GATEWAY_COUNT - online_gateways,
            "sensor_total": settings.MONITOR_GATEWAY_COUNT * settings.MONITOR_SENSOR_COUNT,
            "error_sensors": error_sensors,
            "last_updated": last_ts or None,
            "source": source_label,
        }

    def get_matrix(self, metric: MetricName, key_prefix: str = KEY_PREFIX_REAL) -> dict[str, object]:
        from django.conf import settings
        client = self._client_()
        metric_range = METRIC_RANGES.get(metric, (-1.0, 1.0))
        rows = []

        for gateway_ip in self._gateways():
            cells = []
            for sensor_index in range(1, settings.MONITOR_SENSOR_COUNT + 1):
                raw = client.get(self._sensor_key(gateway_ip, sensor_index, key_prefix))
                if raw:
                    snap = json.loads(raw)
                    value = snap.get(metric)
                    flag = snap.get("display")
                    cells.append({
                        "key": snap["key"],
                        "sensor_index": sensor_index,
                        "value": value if flag is None else None,
                        "display": flag if flag is not None else value,
                        "status": snap.get("status", 0),
                        "online": snap.get("online", False),
                    })
                else:
                    cells.append({
                        "key": f"{gateway_ip}_1_{sensor_index}",
                        "sensor_index": sensor_index,
                        "value": None,
                        "display": "Err",
                        "status": -1,
                        "online": False,
                    })
            rows.append({
                "gateway_ip": gateway_ip,
                "metric": metric,
                "cells": cells,
                "range": {"min": metric_range[0], "max": metric_range[1]},
            })

        source_label = "redis" if key_prefix == KEY_PREFIX_REAL else "fastapi"
        return {
            "metric": metric,
            "range": {"min": metric_range[0], "max": metric_range[1]},
            "rows": rows,
            "source": source_label,
        }

    def get_history(self, gateway_ip: str, sensor_index: int, metric: MetricName) -> dict[str, object]:
        metric_range = METRIC_RANGES.get(metric, (-1.0, 1.0))
        return {
            "gateway_ip": gateway_ip,
            "sensor_index": sensor_index,
            "metric": metric,
            "range": {"min": metric_range[0], "max": metric_range[1]},
            "points": [],
            "source": "redis",
        }
