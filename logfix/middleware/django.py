"""
LogFix Django Middleware
Django MIDDLEWARE 설정에 추가하여 처리되지 않은 예외를 자동 캡처합니다.

Usage (settings.py)::

    MIDDLEWARE = [
        ...
        'logfix.middleware.django.LogfixDjangoMiddleware',
    ]
"""
from __future__ import annotations


class LogfixDjangoMiddleware:
    """
    Django 미들웨어.
    process_exception 훅을 통해 처리되지 않은 예외를 캡처합니다.
    """

    def __init__(self, get_response, client=None) -> None:
        self._get_response = get_response
        self._client = client

    def __call__(self, request):
        response = self._get_response(request)
        return response

    def process_exception(self, request, exception: Exception):
        """Django가 예외를 처리하기 전에 호출됩니다."""
        try:
            client = self._client or self._get_module_client()
            if client is None:
                return None

            method = getattr(request, "method", None)
            path = getattr(request, "path", None)

            # 전체 URL 구성
            try:
                url = request.build_absolute_uri()
            except Exception:
                url = path

            client.capture_error(
                exception,
                extra={
                    "http_method": method,
                    "http_url": url,
                },
            )
        except Exception:
            pass

        # None 반환 → Django가 기본 예외 처리를 계속 수행
        return None

    @staticmethod
    def _get_module_client():
        try:
            import logfix
            return logfix.get_client()
        except Exception:
            return None
