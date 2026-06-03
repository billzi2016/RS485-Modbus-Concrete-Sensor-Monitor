from typing import Literal

from ninja import NinjaAPI

from app.services.dashboard_service import dashboard_service

MetricName = Literal["strain", "temp", "freq", "max_strain"]

api = NinjaAPI(title="RS485 Monitor API")


@api.get("/health")
def health(request) -> dict[str, str]:
    """最小健康检查接口，用于确认 Django Ninja 已成功接入。"""
    return {"status": "ok"}


@api.get("/summary")
def summary(request) -> dict[str, object]:
    """返回顶部总览区摘要数据。"""
    return dashboard_service.get_summary()


@api.get("/matrix/{metric}")
def matrix(request, metric: MetricName) -> dict[str, object]:
    """返回当前指标页的完整矩阵数据。"""
    return dashboard_service.get_matrix(metric)


@api.get("/history/{gateway_ip}/{sensor_index}")
def history(request, gateway_ip: str, sensor_index: int, metric: MetricName = "strain") -> dict[str, object]:
    """返回指定测点最近 10 分钟历史。"""
    return dashboard_service.get_history(gateway_ip, sensor_index, metric)
