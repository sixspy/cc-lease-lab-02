from __future__ import annotations

import re
from datetime import datetime, timezone

键模式 = re.compile(r"^[a-z0-9][a-z0-9\-\.]{1,48}$", re.I)


def 非空(字段: str, 值) -> str:
    text = str(值 or "").strip()
    if not text:
        raise ValueError(f"{字段}不能为空")
    return text


def 正整数(字段: str, 值, 下限: int = 1, 上限: int = 1_000_000) -> int:
    try:
        n = int(值)
    except (TypeError, ValueError):
        raise ValueError(f"{字段}须为整数")
    if n < 下限 or n > 上限:
        raise ValueError(f"{字段}须在 {下限}～{上限} 之间")
    return n


def 池键(值) -> str:
    text = 非空("池键", 值)
    if not 键模式.match(text):
        raise ValueError("池键仅允许字母数字与短横线")
    return text


def 租约号(值) -> str:
    text = 非空("租约号", 值)
    if not 键模式.match(text):
        raise ValueError("租约号格式不合法")
    return text


def 租户(值) -> str:
    text = 非空("租户", 值)
    if len(text) > 64:
        raise ValueError("租户名过长")
    return text


def 此刻() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def 解析时刻(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def 是否到期(到期时刻: str, 宽限分钟: int = 0) -> bool:
    dt = 解析时刻(到期时刻)
    now = datetime.now(timezone.utc)
    return now > dt + __import__("datetime").timedelta(minutes=宽限分钟)