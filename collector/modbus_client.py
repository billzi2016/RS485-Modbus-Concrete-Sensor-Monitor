from __future__ import annotations

import asyncio

from collector.models import GatewayConfig


class ModbusTcpClient:
    """
    Modbus TCP 客户端占位。

    这里先只保留接口形状，后续接真实网关时再补：
    - 建连
    - 发包
    - 读取 233 字节响应帧
    - 超时与重试
    """

    async def read_gateway_frame(self, gateway: GatewayConfig) -> bytes:
        await asyncio.sleep(gateway.poll_interval_ms / 1000)
        raise NotImplementedError("Modbus TCP read is not implemented yet")
