from typing import Literal

from ninja import NinjaAPI

from app.services.dashboard_service import dashboard_service

MetricName = Literal["strain", "temp", "freq", "max_strain"]

api = NinjaAPI(title="RS485 Monitor API")


@api.get("/health")
def health(request) -> dict[str, str]:
    return {"status": "ok"}


@api.get("/summary")
def summary(request, source: str = "real") -> dict[str, object]:
    """source: real | fastapi | mock"""
    return dashboard_service.get_summary(source=source)


@api.get("/matrix/{metric}")
def matrix(request, metric: MetricName, source: str = "real") -> dict[str, object]:
    """source: real | fastapi | mock"""
    return dashboard_service.get_matrix(metric, source=source)


@api.get("/history/{gateway_ip}/{sensor_index}")
def history(request, gateway_ip: str, sensor_index: int, metric: MetricName = "strain") -> dict[str, object]:
    return dashboard_service.get_history(gateway_ip, sensor_index, metric)
