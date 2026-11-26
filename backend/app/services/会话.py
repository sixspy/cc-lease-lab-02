from __future__ import annotations

import os
from typing import Callable

from itsdangerous import BadSignature, URLSafeSerializer

from app.db import 连接

COOKIE = "lease_session"
密钥 = os.environ.get("会话密钥", "lease-lab-dev-secret")
序列化 = URLSafeSerializer(密钥, salt="lease-session")


def 校验登录(账号: str, 密码: str) -> bool:
    conn = 连接()
    try:
        row = conn.execute("SELECT 密码哈希 FROM 用户 WHERE 账号=?", (账号,)).fetchone()
        return bool(row) and str(row["密码哈希"]) == str(密码)
    finally:
        conn.close()


def 签发令牌(账号: str) -> str:
    return 序列化.dumps({"用户": 账号, "已登录": True})


def 解析令牌(token: str | None) -> str | None:
    if not token:
        return None
    try:
        data = 序列化.loads(token)
    except BadSignature:
        return None
    if isinstance(data, dict) and data.get("已登录") and data.get("用户"):
        return str(data["用户"])
    return None


def 从请求取用户(cookies: dict) -> str | None:
    return 解析令牌(cookies.get(COOKIE))


def 当前用户依赖(get_cookies: Callable[[], dict]) -> str | None:
    return 从请求取用户(get_cookies())