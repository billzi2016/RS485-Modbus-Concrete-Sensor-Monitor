from __future__ import annotations

import asyncio
import time

from collector.modbus_client import ModbusTcpClient
from collector.models import GatewayConfig
from collector.parser import parse_sensor_block
from collector.redis_writer import RedisWriter


class GatewayScheduler:
    """
    采集调度器骨架。

    真正接入真实设备时，每个网关会有一个独立 asyncio 任务：
    - 读取固定长度 Modbus TCP 响应
    - 解析 16 个传感器
    - 写入 Redis 最新快照和 10 分钟历史
    """

    def __init__(self, client: ModbusTcpClient, writer: RedisWriter) -> None:
        self.client = client
        self.writer = writer

    async def poll_gateway(self, gateway: GatewayConfig) -> None:
        while True:
            frame = await self.client.read_gateway_frame(gateway)
            data_area = frame[9:233]
            ts = int(time.time())

            for sensor_index in range(16):
                snapshot = parse_sensor_block(data_area, gateway.ip, sensor_index, ts)
                self.writer.write_latest(snapshot)
                self.writer.append_history(snapshot)

            await asyncio.sleep(gateway.poll_interval_ms / 1000)

    async def run(self, gateways: list[GatewayConfig]) -> None:
        tasks = [asyncio.create_task(self.poll_gateway(gateway)) for gateway in gateways]
        await asyncio.gather(*tasks)
