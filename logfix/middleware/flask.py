"""
LogFix Flask Middleware
Flask 요청 컨텍스트(URL, 메서드, 상태 코드)를 에러에 자동 첨부합니다.

Usage::

    from flask import Flask
    from logfix.middleware.flask import LogfixFlaskMiddleware

    app = Flask(__name__)
    LogfixFlaskMiddleware(app)

또는 이미 생성된 앱에 init_app 패턴으로 적용::

    middleware = LogfixFlaskMiddleware()
    middleware.init_app(app)
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class LogfixFlaskMiddleware:
    """
    Flask 에러 처리 미들웨어.
    처리되지 않은 예외를 LogFix 로 자동 캡처합니다.
    """

    def __init__(self, app=None, client=None) -> None:
        """
        Parameters
        ----------
        app:    Flask 앱 인스턴스 (선택). None 이면 init_app() 으로 나중에 등록.
        client: LogfixClient 인스턴스. None 이면 모듈 레벨 클라이언트 사용.
        """
        self._client = client
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        """Flask 앱에 에러 핸들러를 등록합니다."""
        try:
            from flask import request as flask_request

            @app.before_request
            def _logfix_before_request():
                pass  # 향후 요청 컨텍스트 주입 확장 포인트

            @app.after_request
            def _logfix_after_request(response):
                return response

            @app.teardown_request
            def _logfix_teardown(exc):
                if exc is not None:
                    self._capture(exc, flask_request)

        except ImportError:
            raise ImportError(
                "LogFix Flask middleware requires Flask. "
                "Install it with: pip install flask"
            )

    def _capture(self, exc, request) -> None:
        try:
            client = self._client or self._get_module_client()
            if client is None:
                return

            extra = {}
            tags = {}

            try:
                http_method = request.method
                http_url = request.url
            except Exception:
                http_method = None
                http_url = None

            event_id = client.capture_error(
                exc,
                tags=tags,
                extra={
                    "http_method": http_method,
                    "http_url": http_url,
                    **extra,
                },
            )
            # event에 http 컨텍스트 직접 첨부 (내부 빌드 과정에서 처리되므로 여기선 extra로 전달)
        except Exception:
            pass

    @staticmethod
    def _get_module_client():
        try:
            import logfix
            return logfix.get_client()
        except Exception:
            return None
