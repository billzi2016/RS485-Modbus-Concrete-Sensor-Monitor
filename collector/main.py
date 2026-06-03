from __future__ import annotations

import asyncio
import os

from collector.config_loader import load_gateway_configs
from collector.modbus_client import ModbusTcpClient
from collector.redis_writer import RedisWriter
from collector.scheduler import GatewayScheduler


async def main() -> None:
    redis_url = os.getenv("MONITOR_REDIS_URL", "redis://localhost:6379")
    gateways = load_gateway_configs("configs/gateways.json")
    scheduler = GatewayScheduler(
        client=ModbusTcpClient(),
        writer=RedisWriter(redis_url=redis_url),
    )
    await scheduler.run(gateways)


if __name__ == "__main__":
    asyncio.run(main())
