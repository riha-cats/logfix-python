# LogFix

"""
LogFix PYTHON SDK
~~~~~~~~~~~~~~~~~

LogFix는 당신의 로그를 저장하는 것을 넘어, 에러의 근본 원인을 이해하는 초기 구축의 완벽한 선택이죠.
난해한 스택 트레이스를 30초 만에 실행 가능한 해결책으로 변환해보세요!


기본적인 구성:

    >>> import logfix
    >>> logfix.init(api_key="API_KEY")
    >>> logfix.log("서버가 시작됬어요.")
    
... 아니면 막 넣어보죠.

    >>> import logfix
    >>> logfix.init(api_key="API_KEY")
    >>> logfix.log("서버가 시작됬어요.")
    >>> logfix.debug("쿼리 실행!", extra={"sql": "SELECT ..."})
    >>> logfix.info("유저가 로그인했어요.", tags={"user_id": "123"})
    >>> logfix.warn("주의!! 메모리 사용량이 높아요.")
    >>> logfix.error(Exception) # .. 이런식으로 예외 개체도 되고..
    >>> logfix.error("뭔가 잘못됨")  # .. 문자열도 가능!
    >>> logfix.fatal("Fatal")

조금 더 자세한 것을 알아보고 싶다면..
우리 LogFix 에 방문해보세요! <https://logfix.xyz>.

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.

"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .client import LogfixClient
from .config import Config, OverflowPolicy
from .event import Level

__version__ = "1.0.2"
__all__ = [

    # 리셋
    "init",
    "get_client",

    # 단축 API
    "debug",
    "log",
    "info",
    "warn",
    "error",
    "fatal",

    # full API
    "capture_error",
    "capture_message",
    "recover_and_capture",
    "capture_exceptions",

    # control
    "flush",
    "close",

    # public type
    "LogfixClient",
    "Config",
    "Level",
    "OverflowPolicy",
]

# modue level client (single turn)
_client: Optional[LogfixClient] = None

logger = logging.getLogger("logfix")


# 여기서부터는 기본적인 리셋을 담당합니다
def init(
    api_key: str,
    *,
    app_version: str = "unknown",
    endpoint: str = "https://api.logfix.xyz",
    max_batch_size: int = 50,
    flush_interval: float = 5.0,
    queue_size: int = 1000,
    max_retries: int = 3,
    overflow_policy: str = "drop_newest",
    debug: bool = False,
    enabled: bool = True,
) -> LogfixClient:
    """
    LogFix SDK를 초기화 합니다.

    Parameters
    ----------
    api_key:          프로젝트 API Key *(필수)
    app_version:      앱 버전 태그 (예시: '1.2.3')
    endpoint:         Self-hosted 서버 URL
    max_batch_size:   배치 최대 이벤트 수 (기본값: 50)
    flush_interval:   주기적 플러시 간격 초 (기본값: 5)
    queue_size:       내부 버퍼 크기 (기본값: 1000)
    max_retries:      전송 실패 시 최대 재시도 횟수 (기본값: 3)
    overflow_policy:  큐 오버플로우 정책 (타입: drop_newest / drop_oldest / block)
    debug:            True 시 SDK 내부 로그 출력 여부 (Boolean)
    enabled:          False 시 모든 캡처 무시 (Boolean)

    Returns
    -------
    LogfixClient
    """
    global _client

    config = Config(
        api_key=api_key,
        app_version=app_version,
        endpoint=endpoint,
        max_batch_size=max_batch_size,
        flush_interval=flush_interval,
        queue_size=queue_size,
        max_retries=max_retries,
        overflow_policy=overflow_policy,
        debug=debug,
        enabled=enabled,
    )

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # setup
    _client = LogfixClient(config)
    return _client


def get_client() -> Optional[LogfixClient]:
    """
    현재 초기화된 클라이언트를 반환합니다.
    단, init() 전이면 None 상태
    """
    return _client



# 여기서부터는 모듈 공개 API 쪽입니다.
def capture_error(
    exc: BaseException,
    *,
    level: Level = Level.ERROR,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> Optional[str]:
    """
    예외를 캡처합니다-논블로킹

    Returns event_id or None
    """
    if _client is None:
        logger.warning("LogFix: capture_error called before init(). Call logfix.init() first.")
        return None
    return _client.capture_error(exc, level=level, tags=tags, extra=extra, event_id=event_id)


# 메시지 캡쳐
def capture_message(
    message: str,
    *,
    level: Level = Level.INFO,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> Optional[str]:
    """
    메시지를 직접 캡처합니다-논블로킹

    Returns event_id or None
    """
    if _client is None:
        logger.warning("LogFix: capture_message called before init(). Call logfix.init() first.")
        return None
    return _client.capture_message(message, level=level, tags=tags, extra=extra, event_id=event_id)


def recover_and_capture(func: Callable[[], Any]) -> Any:
    """
    func 실행 중 예외 발생 시 자동 캡처 후 re-raise 처리

    이용법:
        ```
        logfix.recover_and_capture(lambda: risky_operation())
        ```
    """
    if _client is None:
        logger.warning("LogFix: recover_and_capture called before init().")
        return func()
    return _client.recover_and_capture(func)


def capture_exceptions(
    *,
    level: Level = Level.ERROR,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    reraise: bool = True,
):
    """
    Context Manager로서 예외를 캡쳐합니다.

    이용법:
        ```
        with logfix.capture_exceptions(reraise=False):
            risky_operation()
        ```
    """
    if _client is None:
        logger.warning("LogFix: capture_exceptions called before init().")
        # return to dummy context
        from contextlib import nullcontext
        return nullcontext()
    return _client.capture_exceptions(level=level, tags=tags, extra=extra, reraise=reraise)


def flush(timeout: float = 10.0) -> None:
    """
    큐 쌓인 것을 한번에 푸쉬.
    """
    if _client is not None:
        _client.flush(timeout=timeout)


def close() -> None:
    """
    SDK 리소스를 Flush 포함하여 정리합니다.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None



# 단축 API
def debug(message: str, **kwargs) -> Optional[str]:
    """logfix.debug('msg')  →  Level.DEBUG"""
    return capture_message(message, level=Level.DEBUG, **kwargs)

def log(message: str, **kwargs) -> Optional[str]:
    """logfix.log('msg')  →  Level.INFO"""
    return capture_message(message, level=Level.INFO, **kwargs)

def info(message: str, **kwargs) -> Optional[str]:
    """logfix.info('msg')  →  Level.INFO"""
    return capture_message(message, level=Level.INFO, **kwargs)

def warn(message: str, **kwargs) -> Optional[str]:
    """logfix.warn('msg')  →  Level.WARNING"""
    return capture_message(message, level=Level.WARNING, **kwargs)

def error(exc_or_message, **kwargs) -> Optional[str]:
    """
    logfix.error(exc)        ... 예외 캡쳐
    logfix.error('message')  ... 문자열 캡쳐
    """
    if isinstance(exc_or_message, BaseException):
        return capture_error(exc_or_message, level=Level.ERROR, **kwargs)
    return capture_message(str(exc_or_message), level=Level.ERROR, **kwargs)

def fatal(exc_or_message, **kwargs) -> Optional[str]:
    """
    logfix.fatal(exc)        ... 예외 캡쳐
    logfix.fatal('message')  ... 문자열 캡쳐
    """
    if isinstance(exc_or_message, BaseException):
        return capture_error(exc_or_message, level=Level.FATAL, **kwargs)
    return capture_message(str(exc_or_message), level=Level.FATAL, **kwargs)