from __future__ import annotations

import json

from collector.models import SensorSnapshot

KEY_PREFIX = "monitor:sensor"
KEY_TTL_SECONDS = 10


class RedisWriter:
    """将解析后的传感器快照写入 Redis，供 Django RedisReader 读取。"""

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        import redis as _redis
        self._client = _redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def _redis_key(self, snapshot: SensorSnapshot) -> str:
        return f"{KEY_PREFIX}:{snapshot.gateway_ip}:{snapshot.sensor_index}"

    def write_latest(self, snapshot: SensorSnapshot) -> None:
        """写最新快照，TTL=10s。Redis key 过期即视为离线。"""
        data = {
            "key": snapshot.key,
            "sensor_index": snapshot.sensor_index,
            "strain": round(snapshot.strain, 3),
            "temp": round(snapshot.temp, 3),
            "freq": float(snapshot.raw_freq),
            "max_strain": round(snapshot.max_strain, 3),
            "status": snapshot.status,
            "display": "Err" if snapshot.status != 0 else None,
            "online": True,   # 能读到帧就算在线；掉线后 key 自动 TTL 过期
            "ts": snapshot.ts,
        }
        self._client.set(self._redis_key(snapshot), json.dumps(data), ex=KEY_TTL_SECONDS)

    def append_history(self, snapshot: SensorSnapshot) -> None:
        # 历史由前端客户端侧累积，服务端无需持久化
        pass
