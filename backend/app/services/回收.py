from __future__ import annotations

import uuid

from app.db import 连接
from app.services import 租约, 校验, 说明


def _留痕(conn, 操作, 租约号="", 详情=""):
    conn.execute(
        "INSERT INTO 操作留痕(时刻,操作,租约号,详情) VALUES (?,?,?,?)",
        (校验.此刻(), 操作, 租约号, 详情),
    )


def 入匣(body: dict) -> dict:
    租约号 = 校验.租约号(body.get("租约号"))
    原因 = str(body.get("原因") or "到期未续")
    row = 说明.租约一条(租约号)
    if not row:
        raise ValueError("无此租约")
    回收号 = str(body.get("回收号") or f"rc-{uuid.uuid4().hex[:8]}")
    conn = 连接()
    try:
        已有 = conn.execute(
            "SELECT 回收号 FROM 回收匣 WHERE 租约号=? AND 状态='待回收'", (租约号,)
        ).fetchone()
        if 已有:
            return dict(
                conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (已有["回收号"],)).fetchone()
            )
        conn.execute(
            """INSERT INTO 回收匣(回收号,租约号,池键,租户,原因,状态,入匣时,处置时)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                回收号,
                租约号,
                row["池键"],
                row["租户"],
                原因,
                "待回收",
                校验.此刻(),
                "",
            ),
        )
        _留痕(conn, "租约入回收匣", 租约号, 原因)
        conn.commit()
        return dict(conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (回收号,)).fetchone())
    finally:
        conn.close()


def 确认回收(回收号: str) -> dict:
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (回收号,)).fetchone()
        if not row:
            raise ValueError("无此回收记录")
        if row["状态"] != "待回收":
            raise ValueError("仅待回收可确认")
        conn.execute(
            "UPDATE 回收匣 SET 状态='已回收', 处置时=? WHERE 回收号=?",
            (校验.此刻(), 回收号),
        )
        租约.标记回收(row["租约号"])
        _留痕(conn, "确认回收", row["租约号"], 回收号)
        conn.commit()
        return dict(conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (回收号,)).fetchone())
    finally:
        conn.close()


def 作废(回收号: str, 原因: str = "误回收") -> dict:
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (回收号,)).fetchone()
        if not row:
            raise ValueError("无此回收记录")
        if row["状态"] != "待回收":
            raise ValueError("仅待回收可作废")
        conn.execute(
            "UPDATE 回收匣 SET 状态='已作废', 处置时=?, 原因=? WHERE 回收号=?",
            (校验.此刻(), 原因, 回收号),
        )
        _留痕(conn, "回收作废", row["租约号"], 原因)
        conn.commit()
        return dict(conn.execute("SELECT * FROM 回收匣 WHERE 回收号=?", (回收号,)).fetchone())
    finally:
        conn.close()


def 扫描并入匣() -> list:
    return 租约.扫描逾期()