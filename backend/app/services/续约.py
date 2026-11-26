from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.db import 连接
from app.services import 校验, 说明


def _留痕(conn, 操作, 租约号, 详情=""):
    conn.execute(
        "INSERT INTO 操作留痕(时刻,操作,租约号,详情) VALUES (?,?,?,?)",
        (校验.此刻(), 操作, 租约号, 详情),
    )


def _默认延长分钟() -> int:
    规 = 说明.租账规()
    try:
        return max(5, int(规.get("默认租期分钟", "120")))
    except ValueError:
        return 120


def 发心跳(body: dict) -> dict:
    租约号 = 校验.租约号(body.get("租约号"))
    模拟失败 = bool(body.get("模拟失败"))
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 租约 WHERE 租约号=?", (租约号,)).fetchone()
        if not row:
            raise ValueError("无此租约")
        if row["状态"] not in ("生效中", "已续约", "待生效"):
            raise ValueError("当前状态不可心跳")
        if row["状态"] == "待生效":
            raise ValueError("请先激活租约再发心跳")
        心跳号 = f"hb-{uuid.uuid4().hex[:8]}"
        结果 = "失败" if 模拟失败 else "成功"
        延迟 = int(body.get("延迟毫秒") or 35)
        说明文 = str(body.get("说明") or "页面手动心跳")
        conn.execute(
            """INSERT INTO 心跳(心跳号,租约号,时刻,结果,延迟毫秒,说明) VALUES (?,?,?,?,?,?)""",
            (心跳号, 租约号, 校验.此刻(), 结果, 延迟, 说明文),
        )
        回报 = {"心跳号": 心跳号, "租约号": 租约号, "结果": 结果}
        if 结果 == "成功":
            延长 = int(body.get("延长分钟") or _默认延长分钟() // 4)
            延长 = 校验.正整数("延长分钟", 延长, 下限=1, 上限=24 * 60)
            新到期 = datetime.now(timezone.utc) + timedelta(minutes=延长)
            iso = 新到期.strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                """UPDATE 租约 SET 状态='已续约', 到期时刻=?, 续约次数=续约次数+1, 更新时=?
                   WHERE 租约号=?""",
                (iso, 校验.此刻(), 租约号),
            )
            回报["新到期时刻"] = iso
            回报["状态"] = "已续约"
        else:
            回报["状态"] = row["状态"]
        _留痕(conn, "心跳续约", 租约号, 结果)
        conn.commit()
        return 回报
    finally:
        conn.close()


def 批量心跳(租约号列表: list[str]) -> list:
    out = []
    for lid in 租约号列表:
        try:
            out.append(发心跳({"租约号": lid}))
        except ValueError as e:
            out.append({"租约号": lid, "错误": str(e)})
    return out


def 最近失败次数(租约号: str, 窗口: int = 5) -> int:
    conn = 连接()
    try:
        rows = conn.execute(
            "SELECT 结果 FROM 心跳 WHERE 租约号=? ORDER BY 时刻 DESC LIMIT ?",
            (租约号, 窗口),
        ).fetchall()
        return sum(1 for r in rows if r["结果"] != "成功")
    finally:
        conn.close()