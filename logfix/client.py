"""
client
~~~~~~

이 모듈은 LogFix 의 핵심 클라이언트입니다.

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from .config import Config
from .context import get_os_info, get_runtime_version, get_stack_trace
from .event import Event, Level
from .queue import EventQueue
from .transport import HttpTransport
from .worker import BackgroundWorker

logger = logging.getLogger("logfix.client")

F = TypeVar("F", bound=Callable[..., Any])


class LogfixClient:
    """
    LogFix SDK 의 핵심 클라이언트

    직접 인스턴스화하거나 모듈 레벨의 logfix.init() 를 사용해야 합니다
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._os_info = get_os_info()
        self._runtime_version = get_runtime_version()
        self._started = False

        if not config.enabled:
            if config.debug:
                logger.debug("LogFix: SDK is disabled (enabled=False). All captures are no-ops.")
            return

        # Inside module reset
        self._queue = EventQueue(
            maxsize=config.queue_size,
            overflow_policy=config.overflow_policy,
            debug=config.debug,
        )
        self._transport = HttpTransport(
            api_key=config.api_key,
            endpoint=config.endpoint,
            max_retries=config.max_retries,
            debug=config.debug,
        )
        self._worker = BackgroundWorker(
            queue=self._queue,
            transport=self._transport,
            max_batch_size=config.max_batch_size,
            flush_interval=config.flush_interval,
            debug=config.debug,
        )

        # >> daemon thread 등의 기타 여부 처리 보완이 필요할 수 있음
        # >> main에서 처리
        self._worker.start()
        self._started = True
        # END

        if config.debug:
            logger.debug(
                "LogFix: SDK initialized. endpoint=%s app_version=%s",
                config.endpoint,
                config.app_version,
            )

    # 공개 API
    def capture_error(
        self,
        exc: BaseException,
        *,
        level: Level = Level.ERROR,
        tags: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        예외를 캡처하여 내부 큐에 적재합니다-논블로킹

        Parameters
        ----------
        exc:       캡처할 예외 객체
        level:     심각도 레벨 (기본값: ERROR)
        tags:      커스텀 태그 dict
        extra:     추가 메타데이터 dict
        event_id:  이벤트 ID override (미지정 시 UUID v4 로 자동생성)

        Returns
        -------
        str | None  성공 시 event_id / 비활성화 상태이면 None
        """
        if not self._config.enabled or not self._started:
            return None
        try:
            event = self._build_event(
                message=self._format_exception(exc),
                level=level,
                stack_trace=get_stack_trace(exc),
                tags=tags,
                extra=extra,
                event_id=event_id,
            )
            self._queue.put(event)
            return event.event_id
        
        # 예외 Slient 처리
        except Exception as e:
            if self._config.debug:
                logger.debug("LogFix: capture_error failed (silent): %s", e)
            return None

    # 메시지 캡쳐
    def capture_message(
        self,
        message: str,
        *,
        level: Level = Level.INFO,
        tags: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        메시지를 예외 없이 직접 캡쳐합니다

        Returns
        -------
        str | None  성공 시 event_id
        """
        if not self._config.enabled or not self._started:
            return None

        try:
            event = self._build_event(
                message=message,
                level=level,
                stack_trace=get_stack_trace(),
                tags=tags,
                extra=extra,
                event_id=event_id,
            )
            self._queue.put(event)
            return event.event_id

        except Exception as e:
            if self._config.debug:
                logger.debug("LogFix: capture_message failed (silent): %s", e)
            return None

    def recover_and_capture(self, func: Callable[[], Any]) -> Any:
        """
        func 을 실행하고 패닉 발생 시 자동으로 캡처 후 re-raise

        사용법:
            ```
            client.recover_and_capture(lambda: risky_operation())
            ```
        """
        try:
            return func()
        except BaseException as exc:
            self.capture_error(exc, level=Level.FATAL)
            raise




    @contextmanager
    def capture_exceptions(
        self,
        *,
        level: Level = Level.ERROR,
        tags: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        reraise: bool = True,
    ) -> Generator[None, None, None]:
        """
        Context manager 방식으로 예외 메시지

        사용법:
            ```
            with client.capture_exceptions(reraise=False):
                risky_operation()
            ```
        """
        try:
            yield
        except BaseException as exc:
            self.capture_error(exc, level=level, tags=tags, extra=extra)
            if reraise:
                raise

    def flush(self, timeout: float = 10.0) -> None:
        """
        현재 큐에 쌓인 모든 이벤트를 즉시 전송
        앱 종료 직전 또는 Only 테스트에서 이용합니다
        """
        if self._started:
            self._worker.flush(timeout=timeout)

    def close(self) -> None:
        """
        SDK 리소스에서 flush()를 포함하여 정리합니다
        """
        if self._started:
            self._worker.stop(flush_remaining=True)
            self._started = False

    # Internal
    def _build_event(
        self,
        message: str,
        level: Level,
        stack_trace: str,
        tags: Optional[Dict[str, str]],
        extra: Optional[Dict[str, Any]],
        event_id: Optional[str],
    ) -> Event:
        kwargs: Dict[str, Any] = dict(
            message=message,
            level=level,
            os_info=self._os_info,
            runtime_version=self._runtime_version,
            app_version=self._config.app_version,
            stack_trace=stack_trace,
            tags=tags or {},
            extra=extra or {},
        )
        if event_id:
            kwargs["event_id"] = event_id
        return Event(**kwargs)

    @staticmethod
    def _format_exception(exc: BaseException) -> str:
        return f"{type(exc).__name__}: {exc}"