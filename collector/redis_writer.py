from __future__ import annotations

from collector.models import SensorSnapshot


class RedisWriter:
    """
    Redis 写入器占位。

    当前仓库还没安装 redis 客户端，所以这里只定义后续 collector -> Redis 的标准入口。
    """

    def write_latest(self, snapshot: SensorSnapshot) -> None:
        raise NotImplementedError("Redis writer is not implemented yet")

    def append_history(self, snapshot: SensorSnapshot) -> None:
        raise NotImplementedError("Redis writer is not implemented yet")
