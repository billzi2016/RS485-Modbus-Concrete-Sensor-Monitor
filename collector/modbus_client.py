from __future__ import annotations

import asyncio
import struct

from collector.models import GatewayConfig

# 每个传感器数据块固定 14 字节：
#   freq(2) + strain(4) + temp(2) + max_strain(4) + status(2)
# Modbus TCP 响应帧头固定 9 字节：
#   MBAP(6: transaction_id 2 + protocol_id 2 + length 2) + unit_id(1) + func_code(1) + byte_count(1)
# 因此 N 个传感器的完整响应帧长度为：
#   frame_len = 9 + N * 14
#   N=1  → 23 字节
#   N=8  → 121 字节
#   N=16 → 233 字节
BYTES_PER_SENSOR = 14
FRAME_HEADER_BYTES = 9
DATA_AREA_OFFSET = FRAME_HEADER_BYTES  # data_area = frame[DATA_AREA_OFFSET:]


def expected_frame_len(sensor_count: int) -> int:
    return FRAME_HEADER_BYTES + sensor_count * BYTES_PER_SENSOR


class ModbusTcpClient:
    """
    Modbus TCP 客户端（Read Holding Registers, FC03）。

    每次 read_gateway_frame 建立一条短连接，读完即关闭。
    后续优化可改为长连接 + 重连池，此处保持简单。
    """

    def __init__(self, timeout: float = 3.0) -> None:
        self._timeout = timeout
        self._tid = 0

    def _next_tid(self) -> int:
        self._tid = (self._tid + 1) & 0xFFFF
        return self._tid

    def _build_request(self, slave_id: int, start_addr: int, n_registers: int) -> bytes:
        # Modbus TCP 请求帧（12 字节）：
        #   MBAP(6): transaction_id, protocol_id=0, length=6
        #   PDU(6): unit_id, fc=0x03, start_addr(2), quantity(2)
        return struct.pack(
            ">HHHBBHH",
            self._next_tid(),  # Transaction ID
            0x0000,            # Protocol ID
            0x0006,            # PDU length
            slave_id,          # Unit ID
            0x03,              # Function Code: Read Holding Registers
            start_addr,        # Starting Address
            n_registers,       # Quantity of Registers
        )

    async def read_gateway_frame(self, gateway: GatewayConfig, sensor_count: int | None = None) -> bytes:
        """
        向网关发送 FC03 请求，读取 sensor_count 个传感器的原始帧。
        返回完整帧（header 9 字节 + data sensor_count*14 字节）。
        """
        n = sensor_count if sensor_count is not None else gateway.sensor_count
        n_registers = n * 7  # 14 字节 / 2 = 7 个寄存器
        request = self._build_request(gateway.slave_id, 0x0000, n_registers)

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(gateway.ip, gateway.port),
            timeout=self._timeout,
        )
        try:
            writer.write(request)
            await writer.drain()

            # 先读 9 字节帧头，判断是否为异常响应
            header = await asyncio.wait_for(
                reader.readexactly(FRAME_HEADER_BYTES),
                timeout=self._timeout,
            )
            if header[7] & 0x80:
                exc_code = header[8] if len(header) > 8 else 0
                raise ValueError(
                    f"Modbus exception 0x{exc_code:02X} from {gateway.ip}:{gateway.port}"
                )

            # 再读数据区
            data_area = await asyncio.wait_for(
                reader.readexactly(n * BYTES_PER_SENSOR),
                timeout=self._timeout,
            )
            return header + data_area
        finally:
            writer.close()
            await writer.wait_closed()
