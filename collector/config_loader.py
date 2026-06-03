from __future__ import annotations

import json
from pathlib import Path

from collector.models import GatewayConfig


def load_gateway_configs(config_path: str | Path) -> list[GatewayConfig]:
    """
    从静态 JSON 加载网关配置。

    当前阶段先保持最简单的文件加载方式，不引入数据库或管理后台。
    """
    path = Path(config_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        GatewayConfig(
            name=item["name"],
            ip=item["ip"],
            port=item.get("port", 502),
            slave_id=item.get("slave_id", 1),
            poll_interval_ms=item.get("poll_interval_ms", 1000),
        )
        for item in payload
    ]
