from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


class MockApiClient:
    """
    访问 test/mock_server.py 的 HTTP 客户端。

    这里故意使用标准库 urllib，避免再引入额外依赖。
    如果远端 mock 服务没启动，调用方会自行回退到本地 mock。
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.MONITOR_MOCK_BASE_URL).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url) and settings.MONITOR_MOCK_ENABLED

    def fetch_json(self, path: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if not self.enabled:
            raise RuntimeError("remote mock service is disabled")

        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=1.5) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError("failed to fetch remote mock data") from exc
