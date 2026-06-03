from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from typing import Literal

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, HTTPException, Query

MetricName = Literal["strain", "temp", "freq", "max_strain"]

app = FastAPI(title="Dam Monitor Mock Server", version="0.1.0")

# 这里固定用 20 个网关、每个 16 个测点，模拟当前阶段的测试规模。
GATEWAY_COUNT = 20
SENSOR_COUNT = 16
# 60 个点、每 10 秒一个点，正好对应最近 10 分钟历史窗口。
HISTORY_POINTS = 60
HISTORY_STEP_SECONDS = 10

# 所有历史图和实时图都按固定量程返回，避免前端自动缩放导致视觉误判。
METRIC_RANGES: dict[MetricName, tuple[float, float]] = {
    "strain": (-5000.0, 5000.0),
    "temp": (-10.0, 40.0),
    "freq": (1000.0, 3000.0),
    "max_strain": (-10000.0, 10000.0),
}

# 当前测试环境按本机 /24 网段模拟，不额外构造 /16 地址空间。
GATEWAYS = [f"10.54.79.{201 + index}" for index in range(GATEWAY_COUNT)]


def clamp(value: float, low: float, high: float) -> float:
    """把模拟值裁剪到指标允许范围内，避免生成不合理的极端值。"""
    return max(low, min(high, value))


def metric_value(
    metric: MetricName, gateway_index: int, sensor_index: int, now: float
) -> float:
    """
    用时间相位 + 网关偏移 + 传感器偏移生成“会波动”的模拟值。

    这里不用随机数，而是用三角函数生成连续变化曲线，目的是让：
    1. 每次请求都有实时变化感
    2. 同一设备前后数据连续，不会像纯随机那样跳变过大
    3. 不同网关、不同测点之间又能看到一定差异
    """
    phase = now / 12.0 + gateway_index * 0.7 + sensor_index * 0.19

    if metric == "strain":
        value = math.sin(phase) * 4200 + math.cos(phase / 3.0) * 450
    elif metric == "temp":
        value = 14 + math.sin(phase / 4.0) * 11 + math.cos(phase / 7.0) * 4
    elif metric == "freq":
        value = 2100 + math.sin(phase / 2.0) * 760 + math.cos(phase / 5.0) * 120
    else:
        value = math.sin(phase / 1.5) * 8600 + math.cos(phase / 6.0) * 900

    low, high = METRIC_RANGES[metric]
    return round(clamp(value, low, high), 3)


def status_code(gateway_index: int, sensor_index: int, now: float) -> int:
    """
    按固定规则周期性制造少量异常状态码。

    这里仍然避免纯随机，目的是让压测和联调时异常分布可重复、可观察。
    返回 0 表示正常，非 0 表示设备状态异常。
    """
    tick = int(now // 15)
    if (gateway_index + sensor_index + tick) % 37 == 0:
        return 2
    if (gateway_index * 3 + sensor_index + tick) % 61 == 0:
        return 4
    return 0


def sensor_key(gateway_ip: str, sensor_index: int) -> str:
    """生成和主系统 PRD 保持一致的测点键格式。"""
    return f"{gateway_ip}_1_{sensor_index + 1}"


def build_sensor_snapshot(
    gateway_ip: str, gateway_index: int, sensor_index: int, now: float
) -> dict[str, object]:
    """
    生成单个测点当前快照。

    online 用于模拟整机在线状态波动；
    display 用于直接给前端返回最终展示值，异常时统一返回 Err，
    这样前端联调时可以直接按工控界面的最终显示逻辑处理。
    """
    code = status_code(gateway_index, sensor_index, now)
    online = (gateway_index + int(now // 20)) % 17 != 0

    return {
        "key": sensor_key(gateway_ip, sensor_index),
        "sensor_index": sensor_index + 1,
        "strain": (
            metric_value("strain", gateway_index, sensor_index, now) if online else None
        ),
        "temp": (
            metric_value("temp", gateway_index, sensor_index, now) if online else None
        ),
        "freq": (
            metric_value("freq", gateway_index, sensor_index, now) if online else None
        ),
        "max_strain": (
            metric_value("max_strain", gateway_index, sensor_index, now)
            if online
            else None
        ),
        "status": code,
        "display": "Err" if (not online or code != 0) else None,
        "ts": int(now),
        "online": online,
    }


def build_gateway_row(
    gateway_ip: str, gateway_index: int, metric: MetricName, now: float
) -> dict[str, object]:
    """
    构造单个网关的一整行矩阵数据。

    返回结果直接对应工控页的“每行一个 IP、每行 16 个方框”的布局。
    这里把 display 和 value 都保留下来，方便前端区分：
    - value：真实数值
    - display：最终展示文本，可能是数值，也可能是 Err
    """
    sensors = [
        build_sensor_snapshot(gateway_ip, gateway_index, sensor_index, now)
        for sensor_index in range(SENSOR_COUNT)
    ]
    metric_cells = []

    for sensor in sensors:
        metric_cells.append(
            {
                "key": sensor["key"],
                "sensor_index": sensor["sensor_index"],
                "value": sensor[metric] if sensor["display"] is None else None,
                "display": (
                    sensor["display"]
                    if sensor["display"] is not None
                    else sensor[metric]
                ),
                "status": sensor["status"],
                "online": sensor["online"],
            }
        )

    return {
        "gateway_ip": gateway_ip,
        "metric": metric,
        "cells": metric_cells,
        "range": {"min": METRIC_RANGES[metric][0], "max": METRIC_RANGES[metric][1]},
    }


@app.get("/health")
def health() -> dict[str, str]:
    """最小健康检查接口，便于本地确认服务是否已经启动。"""
    return {"status": "ok"}


@app.get("/api/summary")
def summary() -> dict[str, object]:
    """
    返回顶部总览区需要的数据。

    这里逐个扫描当前模拟网关和测点，统计在线网关数、离线网关数、异常测点数，
    用于模拟工控页顶部摘要栏。
    """
    now = time.time()
    online_gateways = 0
    error_sensors = 0

    for gateway_index, gateway_ip in enumerate(GATEWAYS):
        gateway_online = False
        for sensor_index in range(SENSOR_COUNT):
            snapshot = build_sensor_snapshot(
                gateway_ip, gateway_index, sensor_index, now
            )
            if snapshot["online"]:
                gateway_online = True
            if snapshot["display"] == "Err":
                error_sensors += 1
        if gateway_online:
            online_gateways += 1

    return {
        "gateway_total": GATEWAY_COUNT,
        "gateway_online": online_gateways,
        "gateway_offline": GATEWAY_COUNT - online_gateways,
        "sensor_total": GATEWAY_COUNT * SENSOR_COUNT,
        "error_sensors": error_sensors,
        "last_updated": int(now),
        "layout": {
            "aspect_ratio": "21:9",
            "row_gateways": GATEWAY_COUNT,
            "cells_per_row": SENSOR_COUNT,
            "legend_position": "top-right",
        },
    }


@app.get("/api/matrix/{metric}")
def matrix(metric: MetricName) -> dict[str, object]:
    """
    返回某个指标 Tab 的完整矩阵数据。

    例如请求 strain 时，前端即可直接得到：
    - 当前量程
    - 20 行网关数据
    - 每行 16 个测点单元
    - 页面风格相关元信息
    """
    now = time.time()
    rows = [
        build_gateway_row(gateway_ip, gateway_index, metric, now)
        for gateway_index, gateway_ip in enumerate(GATEWAYS)
    ]
    return {
        "metric": metric,
        "range": {"min": METRIC_RANGES[metric][0], "max": METRIC_RANGES[metric][1]},
        "rows": rows,
        "legend_position": "top-right",
        "background": "white",
        "cell_style": "gray-box",
    }


@app.get("/api/history/{gateway_ip}/{sensor_index}")
def history(
    gateway_ip: str,
    sensor_index: int,
    metric: MetricName = Query(default="strain"),
) -> dict[str, object]:
    """
    返回单个测点最近 10 分钟历史。

    这里不做真实缓存，而是按当前时间反推 60 个采样点，
    用同一套连续函数生成一条稳定趋势线，方便前端联调固定量程图表。
    """
    if gateway_ip not in GATEWAYS:
        raise HTTPException(status_code=404, detail="gateway not found")
    if sensor_index < 1 or sensor_index > SENSOR_COUNT:
        raise HTTPException(status_code=400, detail="sensor_index out of range")

    gateway_index = GATEWAYS.index(gateway_ip)
    now = time.time()
    points = []

    for point_index in range(HISTORY_POINTS):
        ts = now - (HISTORY_POINTS - point_index - 1) * HISTORY_STEP_SECONDS
        value = metric_value(metric, gateway_index, sensor_index - 1, ts)
        points.append({"ts": int(ts), "value": value})

    return {
        "gateway_ip": gateway_ip,
        "sensor_index": sensor_index,
        "metric": metric,
        "range": {"min": METRIC_RANGES[metric][0], "max": METRIC_RANGES[metric][1]},
        "legend_position": "top-right",
        "points": points,
    }


KEY_PREFIX = "monitor:sensor"


async def feed_redis(redis_url: str, interval: float) -> None:
    """循环向 Redis 写入所有网关传感器快照，模拟 RS485 collector 的数据推送。"""
    client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        while True:
            now = time.time()
            pipe = client.pipeline()
            for gateway_index, gateway_ip in enumerate(GATEWAYS):
                for sensor_index in range(SENSOR_COUNT):
                    snapshot = build_sensor_snapshot(
                        gateway_ip, gateway_index, sensor_index, now
                    )
                    # key 使用 1-based sensor_index 与 RedisReader 保持一致
                    key = f"{KEY_PREFIX}:{gateway_ip}:{sensor_index + 1}"
                    pipe.set(key, json.dumps(snapshot), ex=10)
            await pipe.execute()
            await asyncio.sleep(interval)
    finally:
        await client.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dam Monitor Mock Server")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP server host")
    parser.add_argument("--port", type=int, default=18000, help="HTTP server port")
    parser.add_argument(
        "--feed",
        action="store_true",
        help="同时向 Redis 写入传感器快照（模拟 collector）",
    )
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379",
        help="Redis 连接 URL（仅在 --feed 模式下使用）",
    )
    parser.add_argument(
        "--feed-interval",
        type=float,
        default=1.0,
        help="向 Redis 写入的间隔秒数（默认 1.0）",
    )
    args = parser.parse_args()

    if args.feed:
        config = uvicorn.Config(app, host=args.host, port=args.port)
        server = uvicorn.Server(config)

        async def _main() -> None:
            await asyncio.gather(
                server.serve(),
                feed_redis(args.redis_url, args.feed_interval),
            )

        asyncio.run(_main())
    else:
        uvicorn.run(app, host=args.host, port=args.port)
