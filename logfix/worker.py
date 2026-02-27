"""
worker
~~~~~~

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import atexit
import logging
import signal
import threading
import time
from typing import List, Optional

from .event import Event
from .queue import EventQueue
from .transport import HttpTransport

logger = logging.getLogger("logfix.worker")


class BackgroundWorker:
    """
    데몬 스레드 동작 배치 플러시 워커
    """

    def __init__(
        self,
        queue: EventQueue,
        transport: HttpTransport,
        max_batch_size: int,
        flush_interval: float,
        debug: bool = False,
    ) -> None:
        self._queue = queue
        self._transport = transport
        self._max_batch_size = max_batch_size
        self._flush_interval = flush_interval
        self._debug = debug

        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        self._lock = threading.Lock()
        self._started = False

        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        백그라운드 워커 스레드 시작
        """
        with self._lock:
            if self._started:
                return
            self._started = True

        self._thread = threading.Thread(
            target=self._run,
            name="logfix-worker",
            daemon=True,
        )
        self._thread.start()

        # 종료시에 따른 잔여 플래시
        atexit.register(self._shutdown)
        self._register_signal_handlers()

        if self._debug:
            logger.debug("LogFix: background worker started.")

    def flush(self, timeout: float = 10.0) -> None:
        """
        현재 큐에 쌓인 모든 이벤트를 즉시 전송
        최대 timeout 초 동안 완료를 기다립니다. (*동기 호출)
        """
        if not self._started:
            return

        done_event = threading.Event()

        def _flush_task() -> None:
            self._do_flush()
            done_event.set()

        t = threading.Thread(target=_flush_task, daemon=True)
        t.start()
        done_event.wait(timeout=timeout)

    def stop(self, flush_remaining: bool = True, timeout: float = 10.0) -> None:
        """
        워커를 중지합니다.

        flush_remaining=True 면 잔여 이벤트를 전송합니다.
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        if flush_remaining:
            self._do_flush()

        self._transport.close()


    # internal
    def _run(self) -> None:
        """
        백그라운드 스레드 메인 루프
        """


        last_flush_time = time.monotonic()

        while not self._stop_event.is_set():
            now = time.monotonic()
            elapsed = now - last_flush_time

            # flush_interval 경과 또는 즉시 플러시 이벤트
            interval_expired = elapsed >= self._flush_interval
            flush_requested = self._flush_event.is_set()
            batch_ready = self._queue.size() >= self._max_batch_size

            if interval_expired or flush_requested or batch_ready:
                self._flush_event.clear()
                self._do_flush()
                last_flush_time = time.monotonic()
            else:
                sleep_duration = min(
                    0.05,
                    self._flush_interval - elapsed,
                )
                time.sleep(max(0.005, sleep_duration))

    def _do_flush(self) -> None:
        """
        큐에서 이벤트를 꺼내 배치 전송합니다
        """
        try:
            while True:
                batch = self._queue.drain(self._max_batch_size)
                if not batch:
                    break

                if self._debug:
                    logger.debug("LogFix: flushing batch of %d events", len(batch))

                self._transport.send_batch(batch)
                if len(batch) < self._max_batch_size:
                    break
        except Exception as e:
            if self._debug:
                logger.debug("LogFix: _do_flush error (silent): %s", e)

    def _shutdown(self) -> None:
        """
        atexit 핸들러 - 앱 종료 시 잔여 큐를 플러시
        """
        if self._debug:
            logger.debug("LogFix: shutdown triggered, flushing remaining events...")
        self.stop(flush_remaining=True, timeout=10.0)

    def _register_signal_handlers(self) -> None:
        """
        SIGTERM 수신 시 플러시 후 정상 종료
        기존 시그널 핸들러가 있으면 체이닝
        """
        try:
            original_sigterm = signal.getsignal(signal.SIGTERM)

            def _sigterm_handler(signum, frame):
                if self._debug:
                    logger.debug("LogFix: SIGTERM received, flushing...")
                self._do_flush()
                if callable(original_sigterm):
                    original_sigterm(signum, frame)

            signal.signal(signal.SIGTERM, _sigterm_handler)
        except (ValueError, OSError):
            pass