from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GatewayConfig:
    """单个网关的基础配置。"""

    name: str
    ip: str
    port: int
    slave_id: int
    poll_interval_ms: int


@dataclass(slots=True)
class SensorSnapshot:
    """单个测点的解析结果。"""

    key: str
    raw_freq: int
    strain: float
    temp: float
    max_strain: float
    status: int
    ts: int
