from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GatewayConfig:
    """单个网关的基础配置。"""

    name: str
    ip: str
    port: int
    slave_id: int
    poll_interval_ms: int
    sensor_count: int = 16


@dataclass(slots=True)
class SensorSnapshot:
    """单个测点的解析结果。"""

    key: str
    gateway_ip: str
    sensor_index: int   # 1-based
    raw_freq: int
    strain: float
    temp: float
    max_strain: float
    status: int
    ts: int
