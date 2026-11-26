"""池预热占位：统计禁用池上是否仍有生效租约。"""

from app.db import 连接


def 禁用池风险() -> list:
    conn = 连接()
    try:
        rows = conn.execute(
            """SELECT p.池键, COUNT(l.租约号) AS c FROM 资源池 p
               LEFT JOIN 租约 l ON l.池键=p.池键 AND l.状态 IN ('生效中','已续约')
               WHERE p.启用=0 GROUP BY p.池键 HAVING c>0"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()