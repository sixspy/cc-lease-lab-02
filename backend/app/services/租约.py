from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.db import 连接
from app.services import 资源, 校验, 说明


def _默认租期分钟() -> int:
    规 = 说明.租账规()
    try:
        return max(5, int(规.get("默认租期分钟", "120")))
    except ValueError:
        return 120


def _留痕(conn, 操作, 租约号="", 池键="", 详情=""):
    conn.execute(
        "INSERT INTO 操作留痕(时刻,操作,租约号,池键,详情) VALUES (?,?,?,?,?)",
        (校验.此刻(), 操作, 租约号, 池键, 详情),
    )


def 申领(body: dict) -> dict:
    池键 = 校验.池键(body.get("池键"))
    租户 = 校验.租户(body.get("租户"))
    租约号 = str(body.get("租约号") or f"ls-{uuid.uuid4().hex[:10]}")
    租约号 = 校验.租约号(租约号)
    分钟 = int(body.get("租期分钟") or _默认租期分钟())
    分钟 = 校验.正整数("租期分钟", 分钟, 下限=5, 上限=60 * 24 * 30)
    依据指纹 = body.get("容量指纹", body.get("依据指纹"))
    允许超额 = 说明.租账规().get("允许超额申领") == "1"

    # 与 资源.改容量 抢同一把“池容量锁”，杜绝并发读集合分叉导致的双成功。
    with 资源.池锁(池键):
        conn = 连接()
        conn.isolation_level = None
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM 租约 WHERE 租约号=?", (租约号,)
            ).fetchone():
                raise ValueError("租约号已存在")

            # 容量闸：按现行新容量/最新指纹裁决，并在同事务写“放行”裁决。
            资源.闸口预占(
                conn,
                池键,
                租约号=租约号,
                租户=租户,
                依据指纹=依据指纹,
                允许超额=允许超额,
            )

            现在 = datetime.now(timezone.utc)
            到期 = 现在 + timedelta(minutes=分钟)
            iso = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            生效 = bool(body.get("立即生效", True))
            状态 = "生效中" if 生效 else "待生效"
            conn.execute(
                """INSERT INTO 租约(租约号,池键,租户,状态,申领时,生效时,到期时刻,续约次数,更新时)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    租约号,
                    池键,
                    租户,
                    状态,
                    iso(现在),
                    iso(现在) if 生效 else "",
                    iso(到期),
                    0,
                    iso(现在),
                ),
            )
            _留痕(conn, "申领租约", 租约号, 池键, 租户)
            conn.commit()
        except 资源.容量闸拒绝 as e:
            conn.rollback()
            # 主事务回滚（未占格、无租约），但“余量不足已拒/收紧拒回刷”要留旁路册。
            资源.记录裁决(e.裁决)
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return 说明.租约一条(租约号)


def 激活(租约号: str) -> dict:
    租约号 = 校验.租约号(租约号)
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 租约 WHERE 租约号=?", (租约号,)).fetchone()
        if not row:
            raise ValueError("无此租约")
        if row["状态"] != "待生效":
            raise ValueError("仅待生效租约可激活")
        现在 = 校验.此刻()
        conn.execute(
            "UPDATE 租约 SET 状态='生效中', 生效时=?, 更新时=? WHERE 租约号=?",
            (现在, 现在, 租约号),
        )
        _留痕(conn, "激活租约", 租约号, row["池键"])
        conn.commit()
        return 说明.租约一条(租约号)
    finally:
        conn.close()


def 标记回收(租约号: str) -> dict:
    租约号 = 校验.租约号(租约号)
    conn = 连接()
    try:
        row = conn.execute("SELECT * FROM 租约 WHERE 租约号=?", (租约号,)).fetchone()
        if not row:
            raise ValueError("无此租约")
        if row["状态"] == "已回收":
            return dict(row)
        池键 = row["池键"]
        conn.execute(
            "UPDATE 租约 SET 状态='已回收', 更新时=? WHERE 租约号=?",
            (校验.此刻(), 租约号),
        )
        资源.释放一格(池键)
        _留痕(conn, "租约已回收", 租约号, 池键)
        conn.commit()
        return 说明.租约一条(租约号)
    finally:
        conn.close()


def 扫描逾期() -> list:
    """将已过宽限的生效租约送入回收匣，返回处理列表。"""
    规 = 说明.租账规()
    try:
        宽限 = int(规.get("心跳宽限分钟", "15"))
    except ValueError:
        宽限 = 15
    conn = 连接()
    out = []
    try:
        rows = conn.execute(
            "SELECT * FROM 租约 WHERE 状态 IN ('生效中','已续约')"
        ).fetchall()
        for row in rows:
            if not 校验.是否到期(row["到期时刻"], 宽限):
                continue
            from app.services import 回收

            item = 回收.入匣(
                {
                    "租约号": row["租约号"],
                    "原因": "到期未续",
                }
            )
            标记回收(row["租约号"])
            out.append(item)
        return out
    finally:
        conn.close()