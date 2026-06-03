from __future__ import annotations

import math
import time
from typing import Literal

from django.conf import settings

MetricName = Literal["strain", "temp", "freq", "max_strain"]


class LocalMockProvider:
    """
    本地 mock 数据提供器。

    作用：
    1. 在没有 Redis 和真实 collector 的阶段，让 Django 页面先跑起来
    2. 在 test/mock_server.py 没启动时，仍然能渲染完整页面
    3. 返回结构尽量和后续正式接口保持一致
    """

    metric_ranges: dict[MetricName, tuple[float, float]] = {
        "strain": (-5000.0, 5000.0),
        "temp": (-10.0, 40.0),
        "freq": (1000.0, 3000.0),
        "max_strain": (-10000.0, 10000.0),
    }

    history_points = 60
    history_step_seconds = 10

    @property
    def gateways(self) -> list[str]:
        base_ip = 201
        return [f"10.54.79.{base_ip + index}" for index in range(settings.MONITOR_GATEWAY_COUNT)]

    def clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def metric_value(self, metric: MetricName, gateway_index: int, sensor_index: int, now: float) -> float:
        """
        这里使用连续三角函数生成波动值，而不是纯随机数。

        这样做的好处是：
        - 前端刷新时曲线连续
        - 不同测点之间有差异
        - 同一个测点前后值不会突兀跳变
        """
        phase = now / 12.0 + gateway_index * 0.7 + sensor_index * 0.19

        if metric == "strain":
            value = math.sin(phase) * 4200 + math.cos(phase / 3.0) * 450
        elif metric == "temp":
            value = 14 + math.sin(phase / 4.0) * 11 + math.cos(phase / 7.0) * 4
        elif metric == "freq":
            value = 2100 + math.sin(phase / 2.0) * 760 + math.cos(phase / 5.0) * 120
        else:
            value = math.sin(phase / 1.5) * 8600 + math.cos(phase / 6.0) * 900

        low, high = self.metric_ranges[metric]
        return round(self.clamp(value, low, high), 3)

    def status_code(self, gateway_index: int, sensor_index: int, now: float) -> int:
        """
        周期性制造少量异常值，方便工控页联调 Err 展示。

        仍然避免纯随机，确保异常分布在调试时比较稳定。
        """
        tick = int(now // 15)
        if (gateway_index + sensor_index + tick) % 37 == 0:
            return 2
        if (gateway_index * 3 + sensor_index + tick) % 61 == 0:
            return 4
        return 0

    def sensor_key(self, gateway_ip: str, sensor_index: int) -> str:
        return f"{gateway_ip}_1_{sensor_index + 1}"

    def build_sensor_snapshot(
        self,
        gateway_ip: str,
        gateway_index: int,
        sensor_index: int,
        now: float,
    ) -> dict[str, object]:
        code = self.status_code(gateway_index, sensor_index, now)
        online = (gateway_index + int(now // 20)) % 17 != 0

        return {
            "key": self.sensor_key(gateway_ip, sensor_index),
            "sensor_index": sensor_index + 1,
            "strain": self.metric_value("strain", gateway_index, sensor_index, now) if online else None,
            "temp": self.metric_value("temp", gateway_index, sensor_index, now) if online else None,
            "freq": self.metric_value("freq", gateway_index, sensor_index, now) if online else None,
            "max_strain": self.metric_value("max_strain", gateway_index, sensor_index, now) if online else None,
            "status": code,
            "display": "Err" if (not online or code != 0) else None,
            "ts": int(now),
            "online": online,
        }

    def get_summary(self) -> dict[str, object]:
        now = time.time()
        online_gateways = 0
        error_sensors = 0

        for gateway_index, gateway_ip in enumerate(self.gateways):
            gateway_online = False
            for sensor_index in range(settings.MONITOR_SENSOR_COUNT):
                snapshot = self.build_sensor_snapshot(gateway_ip, gateway_index, sensor_index, now)
                if snapshot["online"]:
                    gateway_online = True
                if snapshot["display"] == "Err":
                    error_sensors += 1
            if gateway_online:
                online_gateways += 1

        return {
            "gateway_total": settings.MONITOR_GATEWAY_COUNT,
            "gateway_online": online_gateways,
            "gateway_offline": settings.MONITOR_GATEWAY_COUNT - online_gateways,
            "sensor_total": settings.MONITOR_GATEWAY_COUNT * settings.MONITOR_SENSOR_COUNT,
            "error_sensors": error_sensors,
            "last_updated": int(now),
            "layout": {
                "aspect_ratio": "21:9",
                "row_gateways": settings.MONITOR_GATEWAY_COUNT,
                "cells_per_row": settings.MONITOR_SENSOR_COUNT,
                "legend_position": "top-right",
            },
            "source": "local-mock",
        }

    def get_matrix(self, metric: MetricName) -> dict[str, object]:
        now = time.time()
        rows = []

        for gateway_index, gateway_ip in enumerate(self.gateways):
            sensors = [
                self.build_sensor_snapshot(gateway_ip, gateway_index, sensor_index, now)
                for sensor_index in range(settings.MONITOR_SENSOR_COUNT)
            ]
            cells = []
            for sensor in sensors:
                cells.append(
                    {
                        "key": sensor["key"],
                        "sensor_index": sensor["sensor_index"],
                        "value": sensor[metric] if sensor["display"] is None else None,
                        "display": sensor["display"] if sensor["display"] is not None else sensor[metric],
                        "status": sensor["status"],
                        "online": sensor["online"],
                    }
                )

            rows.append(
                {
                    "gateway_ip": gateway_ip,
                    "metric": metric,
                    "cells": cells,
                    "range": {"min": self.metric_ranges[metric][0], "max": self.metric_ranges[metric][1]},
                }
            )

        return {
            "metric": metric,
            "range": {"min": self.metric_ranges[metric][0], "max": self.metric_ranges[metric][1]},
            "rows": rows,
            "legend_position": "top-right",
            "background": "white",
            "cell_style": "gray-box",
            "source": "local-mock",
        }

    def get_history(self, gateway_ip: str, sensor_index: int, metric: MetricName) -> dict[str, object]:
        if gateway_ip not in self.gateways:
            raise ValueError("gateway not found")
        if sensor_index < 1 or sensor_index > settings.MONITOR_SENSOR_COUNT:
            raise ValueError("sensor_index out of range")

        gateway_index = self.gateways.index(gateway_ip)
        now = time.time()
        points = []

        for point_index in range(self.history_points):
            ts = now - (self.history_points - point_index - 1) * self.history_step_seconds
            value = self.metric_value(metric, gateway_index, sensor_index - 1, ts)
            points.append({"ts": int(ts), "value": value})

        return {
            "gateway_ip": gateway_ip,
            "sensor_index": sensor_index,
            "metric": metric,
            "range": {"min": self.metric_ranges[metric][0], "max": self.metric_ranges[metric][1]},
            "legend_position": "top-right",
            "points": points,
            "source": "local-mock",
        }
