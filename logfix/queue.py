"""
queue
~~~~~

이 모듈은 LogFix 의 이벤트 큐 시스템입니다.

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import List

from .config import OverflowPolicy
from .event import Event

logger = logging.getLogger("logfix.queue")


class EventQueue:
    """
    thread safety event queue

    overflow policy:
      - DROP_NEWEST: 큐가 가득 차면 새 이벤트를 버림
      - DROP_OLDEST: 오래된 이벤트를 꺼내 버리고 새 이벤트 삽입
      - BLOCK: 공간이 생길 때까지 대기 (가능한 사용 금지 권장 - 앱 블로킹 위험)
    """

    def __init__(
        self,
        maxsize: int,
        overflow_policy: OverflowPolicy,
        debug: bool = False,
    ) -> None:
        self._q: queue.Queue[Event] = queue.Queue(maxsize=maxsize)
        self._policy = overflow_policy
        self._debug = debug
        self._dropped_count = 0

        # > RLock 으로 교체 >> DROP_OLDEST 루프 내부에서 _on_drop을 호출할 때 같은 스레드가 재진입하므로 일반 Lock 사용 시 데드락이 발생
        self._lock = threading.RLock()

    def put(self, event: Event) -> bool:
        """
        이벤트를 큐에 삽입합니다.
        Returns True if enqueued, False if dropped.
        """
        try:
            if self._policy == OverflowPolicy.DROP_NEWEST:
                try:
                    self._q.put_nowait(event)
                    return True
                except queue.Full:
                    self._on_drop(event, reason="queue full (drop_newest)")
                    return False

            elif self._policy == OverflowPolicy.DROP_OLDEST:
                # RLock으로 감싸 경쟁 조건 방지.
                with self._lock:
                    while True:
                        try:
                            self._q.put_nowait(event)
                            return True
                        except queue.Full:
                            try:
                                dropped = self._q.get_nowait()
                                self._on_drop(dropped, reason="queue full (drop_oldest)")
                            except queue.Empty:
                                pass

            elif self._policy == OverflowPolicy.BLOCK:
                # 성능 영향의 우려로 가능하면 사용하지 마세요
                self._q.put(event)
                return True

        except Exception as e:
            if self._debug:
                logger.debug("EventQueue.put failed: %s", e)

        return False

    def drain(self, max_items: int) -> List[Event]:
        """
        최대 max_items 개의 이벤트를 꺼내 반환
        """
        items: List[Event] = []
        for _ in range(max_items):
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                break
        return items

    def drain_all(self) -> List[Event]:
        # maxsize=0 의 위험성 보고로 > 0 변동
        limit = self._q.maxsize if self._q.maxsize > 0 else self._q.qsize()
        return self.drain(max(limit, 1))

    def size(self) -> int:
        return self._q.qsize()

    def is_empty(self) -> bool:
        return self._q.empty()

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def _on_drop(self, event: Event, reason: str) -> None:
        # Lock 에서 RLock 으로 변경
        with self._lock:
            self._dropped_count += 1
        if self._debug:
            logger.debug(
                "LogFix: event dropped [%s] reason=%s event_id=%s",
                event.level,
                reason,
                event.event_id,
            )