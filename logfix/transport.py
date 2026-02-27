"""
transport
~~~~~~~~~

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import json
import logging
import math
import time
from typing import List, Optional, Tuple

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.exceptions import RequestException
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from .event import Event

logger = logging.getLogger("logfix.transport")


# PATH
_INGEST_PATH = "/v1/ingest"
_DEFAULT_TIMEOUT = 10


class TransportResult:
    """전송 결과를 표현합니다."""

    def __init__(
        self,
        success: bool,
        status_code: Optional[int] = None,
        retryable: bool = False,
        retry_after: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after  # seconds to wait before next attempt
        self.error = error

    def __repr__(self) -> str:
        return (
            f"TransportResult(success={self.success}, "
            f"status_code={self.status_code}, "
            f"retryable={self.retryable})"
        )


class HttpTransport:
    """
    LogFix Core API 로 배치 이벤트를 전송

    재시도 정책:
      - 네트워크 오류 또는 5xx -> 지수 백오프 후 재시도 (최대 max_retries회)
      - 429 (Rate Limit) -> X-RateLimit-Remaining 헤더 기반 대기
      - 401 (Auth Error) -> 즉시 포기, 경고 로그 출력
      - 기타 4xx -> 즉시 포기
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        max_retries: int = 3,
        debug: bool = False,
    ) -> None:
        if not _HAS_REQUESTS:
            raise ImportError(
                "LogFix requires 'requests' package."
                "Install it with: pip install requests"
            )
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._max_retries = max_retries
        self._debug = debug
        self._session = self._build_session()

    def _build_session(self) -> "requests.Session":
        session = requests.Session()
        session.headers.update(
            {
                "Content-Type": "application/json",
                "X-API-KEY": self._api_key,
                "X-LogFix-SDK": "python",
                "User-Agent": "logfix-python-sdk/1.0.0",
            }
        )
        return session

    def send_batch(self, events: List[Event]) -> TransportResult:
        """
        이벤트 배치를 전송
        """
        if not events:
            return TransportResult(success=True)

        payload = self._build_payload(events)
        url = f"{self._endpoint}{_INGEST_PATH}"

        attempt = 0
        last_result: TransportResult = TransportResult(success=False, error="not attempted")

        while attempt <= self._max_retries:
            last_result = self._do_request(url, payload)

            if last_result.success:
                if self._debug:
                    logger.debug(
                        "LogFix: batch sent successfully [%d events, attempt %d]",
                        len(events),
                        attempt + 1,
                    )
                return last_result

            if not last_result.retryable:
                if self._debug:
                    logger.debug(
                        "LogFix: non-retryable failure status=%s error=%s",
                        last_result.status_code,
                        last_result.error,
                    )
                return last_result

            # 재시도 대기
            wait_seconds = last_result.retry_after or self._backoff_seconds(attempt)
            if self._debug:
                logger.debug(
                    "LogFix: retrying in %.2fs (attempt %d/%d) status=%s",
                    wait_seconds,
                    attempt + 1,
                    self._max_retries,
                    last_result.status_code,
                )
            time.sleep(wait_seconds)
            attempt += 1

        if self._debug:
            logger.debug(
                "LogFix: batch failed after %d retries, dropping %d events",
                self._max_retries,
                len(events),
            )
        return last_result

    def _do_request(self, url: str, payload: dict) -> TransportResult:
        """
        단일 HTTP 요청을 수행합니다
        예외를 TransportResult로 변환합니다.
        """
        try:
            response = self._session.post(
                url,
                data=json.dumps(payload, default=str),
                timeout=_DEFAULT_TIMEOUT,
            )

            status = response.status_code

            if 200 <= status < 300:
                return TransportResult(success=True, status_code=status)

            if status == 401:
                # 401
                logger.warning(
                    "LogFix: Authentication failed (401). "
                    "Please check your api_key. Events will not be sent."
                )
                return TransportResult(
                    success=False,
                    status_code=status,
                    retryable=False,
                    error="authentication_failed",
                )

            if status == 429:
                # X-RateLimit-Remaining header 기반 대기
                retry_after = self._parse_rate_limit_header(response)
                return TransportResult(
                    success=False,
                    status_code=status,
                    retryable=True,
                    retry_after=retry_after,
                    error="rate_limit_exceeded",
                )

            if 500 <= status < 600:
                # server error -> retry
                return TransportResult(
                    success=False,
                    status_code=status,
                    retryable=True,
                    error=f"server_error_{status}",
                )
            return TransportResult(
                success=False,
                status_code=status,
                retryable=False,
                error=f"client_error_{status}",
            )

        except Exception as exc:
            return TransportResult(
                success=False,
                retryable=True,
                error=str(exc),
            )

    def _parse_rate_limit_header(self, response: "requests.Response") -> float:
        """
        X-RateLimit-Remaining 헤더 값을 읽어 대기 시간을 계산.
        헤더가 없으면 기본 백오프를 반환
        """
        try:
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset_at = response.headers.get("X-RateLimit-Reset") # Unix timestamp

            if reset_at:
                wait = float(reset_at) - time.time()
                return max(1.0, min(wait, 60.0))

            # Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                return max(1.0, float(retry_after))

        except Exception:
            pass

        return 5.0 # default delay

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        """
        지수 백오프 : base=1s, multiplier=2, jitter 포함
        attempt=0 -> ~1s, attempt=1 -> ~2s, attempt=2 -> ~4s
        """
        import random
        base = 2 ** attempt
        jitter = random.uniform(0, base * 0.2)
        return min(base + jitter, 30.0) # Max : 30s gap

    def _build_payload(self, events: List[Event]) -> dict:
        return {
            "events": [e.to_dict() for e in events],
        }

    def close(self) -> None:
        """
        세션 리소스를 정리합니다.
        """
        try:
            self._session.close()
        except Exception:
            pass