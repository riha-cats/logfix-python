"""
event
~~~~~

이 모듈은 LogFix 의 이벤트입니다

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# LEVEL (Enum)
class Level(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"



@dataclass
class Event:
    """
    LogFix 이벤트 단위
    SDK 내부에서 생성됨

    event_id 는 UUID v4 으로 자동 생성됨
    사용자가 직접 override 하려면 event_id 를 명시적으로 전달하세요
    """

    message: str
    level: Level = Level.ERROR
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 자동 수집 컨텍스트
    os_info: str = ""
    runtime_version: str = ""
    app_version: str = "unknown"
    stack_trace: str = ""

    # 사용자 정의
    tags: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    # HTTP 컨텍스트
    http_method: Optional[str] = None
    http_url: Optional[str] = None
    http_status_code: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.event_id,
            "timestamp": self.timestamp,
            "level": self.level.value.upper(),
            "message": self.message,
            "app_version": self.app_version,
        }

        if self.os_info:
            payload["os_version"] = self.os_info
        if self.runtime_version:
            payload["platform"] = self.runtime_version
        if self.stack_trace:
            payload["stacktrace"] = self.stack_trace
        if self.tags:
            payload["tags"] = self.tags
        if self.extra:
            payload["extra"] = self.extra
        if self.http_method is not None:
            payload["http"] = {
                "method": self.http_method,
                "url": self.http_url,
                "status_code": self.http_status_code,
            }

        return payload