"""
config
~~~~~~

이 모듈은 LogFix 의 설정입니다.

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

# import re
# 쓰다가 삭제
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# 오버플로우 정책
class OverflowPolicy(str, Enum):
    DROP_NEWEST = "drop_newest"
    DROP_OLDEST = "drop_oldest"
    BLOCK = "block"



# ============================================
DEFAULT_ENDPOINT = "https://api.logfix.xyz"
DEFAULT_MAX_BATCH_SIZE = 50
DEFAULT_FLUSH_INTERVAL = 5.0
DEFAULT_QUEUE_SIZE = 1000
DEFAULT_MAX_RETRIES = 3
# ============================================


@dataclass
class Config:
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
    """

    api_key: str
    app_version: str = "unknown"
    endpoint: str = DEFAULT_ENDPOINT
    max_batch_size: int = DEFAULT_MAX_BATCH_SIZE
    flush_interval: float = DEFAULT_FLUSH_INTERVAL
    queue_size: int = DEFAULT_QUEUE_SIZE
    max_retries: int = DEFAULT_MAX_RETRIES
    overflow_policy: OverflowPolicy = OverflowPolicy.DROP_NEWEST
    debug: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        self._validate()


    # 검증
    def _validate(self) -> None:
        # api key 가 empty 상태인가?
        if not self.api_key or not isinstance(self.api_key, str):
            raise ValueError("LogFix: api_key is required and must be a non-empty string.")
        
        # batch size 가 1 미만인가?
        if self.max_batch_size < 1:
            raise ValueError("LogFix: max_batch_size must be >= 1.")

        # flush interval 값이 0 이하인가?
        if self.flush_interval <= 0:
            raise ValueError("LogFix: flush_interval must be > 0.")

        # queue size 가 1 미만인가?
        if self.queue_size < 1:
            raise ValueError("LogFix: queue_size must be >= 1.")

        # 최대 시도 횟수가 0 미만인가?
        if self.max_retries < 0:
            raise ValueError("LogFix: max_retries must be >= 0.")

        # END


        # endpoint 후행 슬래시 정규화
        self.endpoint = self.endpoint.rstrip("/")

        # endpoint 의 startswitch
        if not self.endpoint.startswith(("http://", "https://")):
            raise ValueError("LogFix: endpoint must start with http:// or https://")

        # overflow_policy 문자열 -> Enum 변환 허용
        if isinstance(self.overflow_policy, str):
            try:
                self.overflow_policy = OverflowPolicy(self.overflow_policy)
            except ValueError:
                valid = [p.value for p in OverflowPolicy]
                raise ValueError(
                    f"LogFix: overflow_policy must be one of {valid}, got '{self.overflow_policy}'."
                )