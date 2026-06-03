from __future__ import annotations

import asyncio
import logging
import time

from collector.modbus_client import DATA_AREA_OFFSET, ModbusTcpClient
from collector.models import GatewayConfig
from collector.parser import parse_sensor_block
from collector.redis_writer import RedisWriter

logger = logging.getLogger(__name__)


class GatewayScheduler:
    """
    采集调度器。每个网关对应一个独立 asyncio 任务，循环轮询：
    读 Modbus TCP → 解析 N 个传感器 → 写 Redis 最新快照。
    """

    def __init__(self, client: ModbusTcpClient, writer: RedisWriter) -> None:
        self.client = client
        self.writer = writer

    async def poll_gateway(self, gateway: GatewayConfig) -> None:
        while True:
            try:
                frame = await self.client.read_gateway_frame(gateway, gateway.sensor_count)
                data_area = frame[DATA_AREA_OFFSET:]
                ts = int(time.time())

                for sensor_index in range(gateway.sensor_count):
                    snapshot = parse_sensor_block(data_area, gateway.ip, sensor_index, ts)
                    self.writer.write_latest(snapshot)

            except Exception as exc:
                logger.warning("poll_gateway %s failed: %s", gateway.ip, exc)

            await asyncio.sleep(gateway.poll_interval_ms / 1000)

    async def run(self, gateways: list[GatewayConfig]) -> None:
        tasks = [asyncio.create_task(self.poll_gateway(gateway)) for gateway in gateways]
        await asyncio.gather(*tasks)
