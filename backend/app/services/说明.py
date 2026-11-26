from __future__ import annotations

from app.db import 连接
from app.services import 校验


def 租账规() -> dict:
    conn = 连接()
    try:
        rows = conn.execute("SELECT 键,值 FROM 租账规").fetchall()
        return {r["键"]: r["值"] for r in rows}
    finally:
        conn.close()


def 改租账规(body: dict) -> dict:
    conn = 连接()
    try:
        for k, v in body.items():
            键 = 校验.非空("键", k)
            值 = 校验.非空("值", v)
            conn.execute(
                "INSERT INTO 租账规(键,值) VALUES (?,?) ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
                (键, 值),
            )
        conn.commit()
        return 租账规()
    finally:
        conn.close()


def 概览() -> dict:
    conn = 连接()
    try:
        def c(sql, *a):
            return conn.execute(sql, a).fetchone()[0]

        return {
            "资源池数": c("SELECT COUNT(*) FROM 资源池"),
            "启用池": c("SELECT COUNT(*) FROM 资源池 WHERE 启用=1"),
            "租约总数": c("SELECT COUNT(*) FROM 租约"),
            "待生效": c("SELECT COUNT(*) FROM 租约 WHERE 状态='待生效'"),
            "生效中": c("SELECT COUNT(*) FROM 租约 WHERE 状态 IN ('生效中','已续约')"),
            "已回收": c("SELECT COUNT(*) FROM 租约 WHERE 状态='已回收'"),
            "心跳条数": c("SELECT COUNT(*) FROM 心跳"),
            "回收匣待处置": c("SELECT COUNT(*) FROM 回收匣 WHERE 状态='待回收'"),
            "互证报告数": c("SELECT COUNT(*) FROM 互证报告"),
            "租账规": 租账规(),
        }
    finally:
        conn.close()


def 仓情() -> dict:
    return {
        "主链": "资源池 → 申领租约 → 心跳续约 → 到期回收匣 → 租账互证对齐池占用",
        "领域": "应用开发全栈 · 资源租约台",
        "技术": "FastAPI + 多页原生 JS · 左侧栏冷灰琥珀",
    }


def 资源池列表() -> list:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 资源池 ORDER BY 池键").fetchall()]
    finally:
        conn.close()


def 租约列表(状态: str | None = None) -> list:
    conn = 连接()
    try:
        if 状态:
            rows = conn.execute(
                "SELECT * FROM 租约 WHERE 状态=? ORDER BY 更新时 DESC", (状态,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM 租约 ORDER BY 更新时 DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def 租约一条(租约号: str) -> dict | None:
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 租约 WHERE 租约号=?", (租约号,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def 心跳列表(租约号: str | None = None) -> list:
    conn = 连接()
    try:
        if 租约号:
            rows = conn.execute(
                "SELECT * FROM 心跳 WHERE 租约号=? ORDER BY 时刻 DESC", (租约号,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM 心跳 ORDER BY 时刻 DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def 回收列表() -> list:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 回收匣 ORDER BY 入匣时 DESC").fetchall()]
    finally:
        conn.close()


def 互证列表() -> list:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 互证报告 ORDER BY 报告号 DESC").fetchall()]
    finally:
        conn.close()


def 留痕列表() -> list:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute("SELECT * FROM 操作留痕 ORDER BY 编号 DESC LIMIT 80").fetchall()
        ]
    finally:
        conn.close()