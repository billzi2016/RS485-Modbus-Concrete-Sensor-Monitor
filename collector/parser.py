from __future__ import annotations

from collector.models import SensorSnapshot


def parse_sensor_block(data_area: bytes, gateway_ip: str, sensor_index: int, ts: int) -> SensorSnapshot:
    """
    按 PRD 里的 14 字节布局解析单个传感器块。
    sensor_index 为 0-based 输入，SensorSnapshot.sensor_index 存 1-based。
    """
    offset = sensor_index * 14
    raw_freq = (data_area[offset] << 8) | data_area[offset + 1]

    scaled_strain = (
        (data_area[offset + 2] << 24)
        | (data_area[offset + 3] << 16)
        | (data_area[offset + 4] << 8)
        | data_area[offset + 5]
    )
    if scaled_strain & 0x80000000:
        scaled_strain -= 0x100000000

    scaled_temp = (data_area[offset + 6] << 8) | data_area[offset + 7]
    if scaled_temp & 0x8000:
        scaled_temp -= 0x10000

    scaled_max_strain = (
        (data_area[offset + 8] << 24)
        | (data_area[offset + 9] << 16)
        | (data_area[offset + 10] << 8)
        | data_area[offset + 11]
    )
    if scaled_max_strain & 0x80000000:
        scaled_max_strain -= 0x100000000

    status = (data_area[offset + 12] << 8) | data_area[offset + 13]
    idx_1based = sensor_index + 1

    return SensorSnapshot(
        key=f"{gateway_ip}_1_{idx_1based}",
        gateway_ip=gateway_ip,
        sensor_index=idx_1based,
        raw_freq=raw_freq,
        strain=scaled_strain / 1000.0,
        temp=scaled_temp / 100.0,
        max_strain=scaled_max_strain / 1000.0,
        status=status,
        ts=ts,
    )
