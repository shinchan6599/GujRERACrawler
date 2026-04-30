import ssl
from typing import Any

import certifi
import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings


class GujReraClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = structlog.get_logger("gujrera.client")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.gujrera_timeout_connect,
                read=settings.gujrera_timeout_read,
                write=settings.gujrera_timeout_read,
                pool=settings.gujrera_timeout_connect,
            ),
            limits=httpx.Limits(
                max_connections=settings.gujrera_max_connections,
                max_keepalive_connections=settings.gujrera_max_keepalive_connections,
            ),
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "User-Agent": "GujRERA-Gateway/1.0",
            },
            verify=self._build_ssl_context(),
        )

    def _build_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(cafile=certifi.where())
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            context.options |= ssl.OP_LEGACY_SERVER_CONNECT
        return context

    async def close(self) -> None:
        await self._client.aclose()

    def absolute_url(self, path: str) -> str:
        return f"{self.settings.gujrera_base_url.rstrip('/')}{path}"

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(
            (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.ProxyError,
                httpx.HTTPStatusError,
            )
        ),
    )
    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        response = await self._client.request(
            method,
            self.absolute_url(path),
            json=json_body,
            headers=headers,
        )
        if response.status_code >= 500:
            response.raise_for_status()
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def get_json(
        self,
        path: str,
        *,
        endpoint_name: str,
        project_reg_id: int | None = None,
    ) -> Any:
        try:
            return await self._request_json("GET", path)
        except httpx.HTTPStatusError as exc:
            self.logger.warning(
                "gujrera_http_error",
                endpoint=endpoint_name,
                path=path,
                project_reg_id=project_reg_id,
                status_code=exc.response.status_code,
            )
            return None
        except Exception as exc:  # pragma: no cover - network path
            self.logger.warning(
                "gujrera_request_failed",
                endpoint=endpoint_name,
                path=path,
                project_reg_id=project_reg_id,
                error=str(exc),
            )
            return None

    async def post_json(
        self,
        path: str,
        *,
        json_body: Any,
        endpoint_name: str,
        project_reg_id: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        try:
            return await self._request_json(
                "POST",
                path,
                json_body=json_body,
                headers=headers,
            )
        except httpx.HTTPStatusError as exc:
            self.logger.warning(
                "gujrera_http_error",
                endpoint=endpoint_name,
                path=path,
                project_reg_id=project_reg_id,
                status_code=exc.response.status_code,
            )
            return None
        except Exception as exc:  # pragma: no cover - network path
            self.logger.warning(
                "gujrera_request_failed",
                endpoint=endpoint_name,
                path=path,
                project_reg_id=project_reg_id,
                error=str(exc),
            )
            return None
