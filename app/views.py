from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """渲染工控风格监控首页，数据通过前端轮询 Django Ninja 接口获取。"""
    context = {
        "default_metric": "strain",
        "refresh_ms": settings.MONITOR_REFRESH_MS,
        "metrics": [
            ("strain", "应变"),
            ("max_strain", "最大应变"),
            ("temp", "温度"),
            ("freq", "频率"),
        ],
    }
    return render(request, "app/dashboard.html", context)
