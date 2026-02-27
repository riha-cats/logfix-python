"""
LogFix FastAPI Middleware
ASGI 미들웨어로 FastAPI / Starlette 앱에 에러 캡처를 추가합니다.

Usage::

    from fastapi import FastAPI
    from logfix.middleware.fastapi import LogfixFastAPIMiddleware

    app = FastAPI()
    app.add_middleware(LogfixFastAPIMiddleware)
"""
from __future__ import annotations

from typing import Optional


class LogfixFastAPIMiddleware:
    """
    Starlette / FastAPI ASGI 미들웨어.
    각 요청에서 발생한 처리되지 않은 예외를 자동 캡처합니다.
    """

    def __init__(self, app, client=None) -> None:
        """
        Parameters
        ----------
        app:    ASGI 앱
        client: LogfixClient. None 이면 모듈 레벨 클라이언트 사용.
        """
        self._app = app
        self._client = client

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        try:
            await self._app(scope, receive, send)
        except Exception as exc:
            self._capture(exc, scope)
            raise

    def _capture(self, exc: Exception, scope: dict) -> None:
        try:
            client = self._client or self._get_module_client()
            if client is None:
                return

            method = scope.get("method", "")
            path = scope.get("path", "")
            server = scope.get("server")
            scheme = scope.get("scheme", "http")

            if server:
                host, port = server
                url = f"{scheme}://{host}:{port}{path}"
            else:
                url = path

            client.capture_error(
                exc,
                extra={
                    "http_method": method,
                    "http_url": url,
                    "asgi_type": scope.get("type"),
                },
            )
        except Exception:
            pass

    @staticmethod
    def _get_module_client():
        try:
            import logfix
            return logfix.get_client()
        except Exception:
            return None
