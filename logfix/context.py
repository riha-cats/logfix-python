"""
context
~~~~~~~

이 모듈은 LogFix 의 컨텍스트 매니저 부분입니다.

:copyright: (c) 2026 by 나는리하
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import platform
import sys
import traceback
from typing import Optional

# ===================================================================================
def get_os_info() -> str:
    """
    OS 및 버전 정보 서버 반환
    """
    try:
        system = platform.system().lower()
        release = platform.release()

        # linux os 의 경우 추가 버전 리턴시도
        # >> 추후 버전에서 삭제할 의향 있음. PPS가 높아지면 지연 발생 가능성 있음
        # >> If there's a smart developer who can fix this, please contact me :)
        if system == "linux":
            try:
                import distro  # type: ignore  # optional dependency
                distro_name = distro.name(pretty=False).lower().replace(" ", "-")
                distro_version = distro.version()
                return f"linux-{distro_name}-{distro_version}"
            except ImportError:
                pass


            # /etc/os-release pasing 시도
            try:
                os_info = _parse_os_release()
                if os_info:
                    return os_info
            except Exception:
                pass
        return f"{system}-{release}"
    except Exception:
        return "unknown"

# OS 릴리즈 파서
def _parse_os_release() -> Optional[str]:
    """
    Linux /etc/os-release 파싱
    """
    info: dict = {}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k] = v.strip('"')
    except FileNotFoundError:
        return None

    name = info.get("ID", "linux").lower()
    version = info.get("VERSION_ID", "")
    return f"linux-{name}-{version}" if version else f"linux-{name}"
# ===================================================================================

# Python runtime
def get_runtime_version() -> str:
    """
    Python 런타임 버전 반환
    """
    try:
        v = sys.version_info
        return f"python{v.major}.{v.minor}.{v.micro}"
    except Exception:
        return "python-unknown"  # 아마... 가능성은 별로 없을듯 SDK 오류 방지용


def get_stack_trace(exc: Optional[BaseException] = None) -> str:
    """
    예외 객체로부터 스택트레이스 문자열 반환
    exc 가 None 일 경우에는 현재 실행 컨텍스트의 스택이 반환됩니다
    """
    try:
        if exc is not None:
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        else:
            # 현재 스택 캡쳐
            tb_lines = traceback.format_stack()
        return "".join(tb_lines).strip()
    except Exception:
        return ""