from __future__ import annotations

from app.db import 连接
from app.services import 校验, 说明


def _留痕(conn, 操作, 池键="", 详情=""):
    conn.execute(
        "INSERT INTO 操作留痕(时刻,操作,池键,详情) VALUES (?,?,?,?)",
        (校验.此刻(), 操作, 池键, 详情),
    )


def 登记(body: dict) -> dict:
    池键 = 校验.池键(body.get("池键"))
    名称 = 校验.非空("名称", body.get("名称"))
    容量 = 校验.正整数("容量", body.get("容量", 100), 下限=1)
    说明文 = str(body.get("说明") or "")
    conn = 连接()
    try:
        已有 = conn.execute("SELECT 池键 FROM 资源池 WHERE 池键=?", (池键,)).fetchone()
        if 已有:
            raise ValueError("池键已存在")
        conn.execute(
            """INSERT INTO 资源池(池键,名称,容量,已占,启用,说明,更新时)
               VALUES (?,?,?,?,1,?,?)""",
            (池键, 名称, 容量, 0, 说明文, 校验.此刻()),
        )
        _留痕(conn, "登记资源池", 池键, 名称)
        conn.commit()
        return 一条(池键)
    finally:
        conn.close()


def 一条(池键: str) -> dict:
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 资源池 WHERE 池键=?", (池键,)).fetchone()
        if not row:
            raise ValueError("无此资源池")
        return dict(row)
    finally:
        conn.close()


def 改容量(池键: str, 新容量: int) -> dict:
    池键 = 校验.池键(池键)
    容量 = 校验.正整数("容量", 新容量, 下限=1)
    conn = 连接()
    try:
        row = conn.execute("SELECT 已占 FROM 资源池 WHERE 池键=?", (池键,)).fetchone()
        if not row:
            raise ValueError("无此资源池")
        if int(row["已占"]) > 容量:
            raise ValueError("容量不能低于当前已占")
        conn.execute(
            "UPDATE 资源池 SET 容量=?, 更新时=? WHERE 池键=?",
            (容量, 校验.此刻(), 池键),
        )
        _留痕(conn, "调整池容量", 池键, str(容量))
        conn.commit()
        return 一条(池键)
    finally:
        conn.close()


def 改启用(池键: str, 启用: bool) -> dict:
    池键 = 校验.池键(池键)
    conn = 连接()
    try:
        if not conn.execute("SELECT 1 FROM 资源池 WHERE 池键=?", (池键,)).fetchone():
            raise ValueError("无此资源池")
        conn.execute(
            "UPDATE 资源池 SET 启用=?, 更新时=? WHERE 池键=?",
            (1 if 启用 else 0, 校验.此刻(), 池键),
        )
        _留痕(conn, "切换池启用", 池键, "启用" if 启用 else "禁用")
        conn.commit()
        return 一条(池键)
    finally:
        conn.close()


def 预占一格(池键: str) -> None:
    conn = 连接()
    try:
        row = conn.execute(
            "SELECT 容量,已占,启用 FROM 资源池 WHERE 池键=?", (池键,)
        ).fetchone()
        if not row:
            raise ValueError("无此资源池")
        if not int(row["启用"]):
            raise ValueError("资源池未启用")
        已占 = int(row["已占"])
        容量 = int(row["容量"])
        规 = 说明.租账规()
        if 规.get("允许超额申领") != "1" and 已占 >= 容量:
            raise ValueError("资源池已满")
        conn.execute(
            "UPDATE 资源池 SET 已占=已占+1, 更新时=? WHERE 池键=?",
            (校验.此刻(), 池键),
        )
        conn.commit()
    finally:
        conn.close()


def 释放一格(池键: str) -> None:
    conn = 连接()
    try:
        row = conn.execute("SELECT 已占 FROM 资源池 WHERE 池键=?", (池键,)).fetchone()
        if not row:
            return
        已占 = max(0, int(row["已占"]) - 1)
        conn.execute(
            "UPDATE 资源池 SET 已占=?, 更新时=? WHERE 池键=?",
            (已占, 校验.此刻(), 池键),
        )
        conn.commit()
    finally:
        conn.close()