from __future__ import annotations

import asyncio

from collector.config_loader import load_gateway_configs
from collector.modbus_client import ModbusTcpClient
from collector.redis_writer import RedisWriter
from collector.scheduler import GatewayScheduler


async def main() -> None:
    gateways = load_gateway_configs("configs/gateways.json")
    scheduler = GatewayScheduler(client=ModbusTcpClient(), writer=RedisWriter())
    await scheduler.run(gateways)


if __name__ == "__main__":
    asyncio.run(main())
