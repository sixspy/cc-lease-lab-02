from __future__ import annotations

from app.db import 连接
from app.services import 校验, 说明


def 租约台账(池键: str | None = None) -> dict:
    conn = 连接()
    try:
        池列表 = 说明.资源池列表()
        if 池键:
            池列表 = [p for p in 池列表 if p["池键"] == 池键]
        明细 = []
        for p in 池列表:
            租约 = conn.execute(
                "SELECT 状态, COUNT(*) AS c FROM 租约 WHERE 池键=? GROUP BY 状态",
                (p["池键"],),
            ).fetchall()
            状态分布 = {r["状态"]: r["c"] for r in 租约}
            明细.append(
                {
                    "池键": p["池键"],
                    "名称": p["名称"],
                    "容量": p["容量"],
                    "已占": p["已占"],
                    "启用": bool(p["启用"]),
                    "状态分布": 状态分布,
                    "生效计数": 状态分布.get("生效中", 0) + 状态分布.get("已续约", 0),
                }
            )
        return {"生成于": 校验.此刻(), "池数": len(明细), "明细": 明细}
    finally:
        conn.close()


def 租户汇总() -> list:
    conn = 连接()
    try:
        rows = conn.execute(
            """SELECT 租户, COUNT(*) AS 租约数,
               SUM(CASE WHEN 状态 IN ('生效中','已续约') THEN 1 ELSE 0 END) AS 活跃数
               FROM 租约 GROUP BY 租户 ORDER BY 活跃数 DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()