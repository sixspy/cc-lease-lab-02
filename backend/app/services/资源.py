from __future__ import annotations

import threading

from app.db import 连接
from app.services import 校验, 说明


# ---------------------------------------------------------------------------
# 容量工程形态（钉死）：
#   形式一「容量指纹 + 切流账册」为主闸 —— 每次改容量先落 容量切流账 指纹，
#   申领在同池锁 + BEGIN IMMEDIATE 原子条件更新内按现行新容量/最新指纹裁决，
#   携旧指纹的在途申领一律“容量已收紧·拒回刷”。
#   同时双写两轨：主账（资源池已占/租约/操作留痕）与旁路 容量裁决账
#   （每次放行/拒绝及其读集合）。读集合分叉见 互证.py 的影子口径。
# ---------------------------------------------------------------------------

_锁表护 = threading.Lock()
_池锁表: dict[str, threading.RLock] = {}


def 池锁(池键: str) -> threading.RLock:
    """同一资源池的“同一次容量锁”：改容量与申领抢的是同一把。"""
    with _锁表护:
        lk = _池锁表.get(池键)
        if lk is None:
            lk = threading.RLock()
            _池锁表[池键] = lk
        return lk


class 容量闸拒绝(ValueError):
    """容量闸口的结构化拒绝；``裁决`` 会落入旁路容量裁决账。"""

    def __init__(self, 消息: str, 裁决: dict):
        super().__init__(消息)
        self.裁决 = 裁决


def _留痕(conn, 操作, 池键="", 详情=""):
    conn.execute(
        "INSERT INTO 操作留痕(时刻,操作,池键,详情) VALUES (?,?,?,?)",
        (校验.此刻(), 操作, 池键, 详情),
    )


def 容量口径(容量: int, 已占: int) -> dict:
    """新容量口径下的可读字段；超过新容量的部分单列为旧容量影子占用。"""
    容量 = int(容量)
    已占 = int(已占)
    return {
        "可申领余量": max(0, 容量 - 已占),
        "新容量内合法占用": min(已占, 容量),
        "影子占用": max(0, 已占 - 容量),
        "是否超容": 已占 > 容量,
    }


def 增补实况(d: dict) -> dict:
    d.update(容量口径(d.get("容量", 0), d.get("已占", 0)))
    d.setdefault("容量指纹", 0)
    return d


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
            """INSERT INTO 资源池(池键,名称,容量,已占,启用,说明,容量指纹,更新时)
               VALUES (?,?,?,?,1,?,0,?)""",
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


def 容量实况(池键: str) -> dict:
    d = 一条(池键)
    增补实况(d)
    conn = 连接()
    try:
        last = conn.execute(
            "SELECT 是否收紧,旧容量,新容量,时刻 FROM 容量切流账 WHERE 池键=? "
            "ORDER BY 指纹 DESC LIMIT 1",
            (池键,),
        ).fetchone()
    except Exception:
        last = None
    finally:
        conn.close()
    if last:
        d["最近收紧"] = dict(last)
        d["容量已收紧"] = bool(last["是否收紧"])
    else:
        d["最近收紧"] = None
        d["容量已收紧"] = False
    return d


def 改容量(池键: str, 新容量: int, 操作人: str = "") -> dict:
    池键 = 校验.池键(池键)
    容量 = 校验.正整数("容量", 新容量, 下限=1)
    with 池锁(池键):
        conn = 连接()
        conn.isolation_level = None
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT 容量,已占,容量指纹 FROM 资源池 WHERE 池键=?", (池键,)
            ).fetchone()
            if not row:
                raise ValueError("无此资源池")
            旧容量 = int(row["容量"])
            已占 = int(row["已占"])
            收紧 = 容量 < 旧容量
            口径 = 容量口径(容量, 已占)
            余量 = 口径["可申领余量"]
            影子 = 口径["影子占用"]
            说明文字 = (
                f"{旧容量}->{容量}；现行已占{已占}；当场重算可申领余量{余量}"
            )
            if 收紧:
                说明文字 += "；容量已收紧"
                if 影子:
                    说明文字 += f"，旧容量影子占用{影子}格为收紧前既占，保留不挤掉，新申领按{容量}拦"
            cur = conn.execute(
                """INSERT INTO 容量切流账
                   (时刻,池键,旧容量,新容量,收紧前已占,可申领余量,是否收紧,操作人,说明)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    校验.此刻(),
                    池键,
                    旧容量,
                    容量,
                    已占,
                    余量,
                    1 if 收紧 else 0,
                    操作人,
                    说明文字,
                ),
            )
            指纹 = int(cur.lastrowid)
            conn.execute(
                "UPDATE 资源池 SET 容量=?, 容量指纹=?, 更新时=? WHERE 池键=?",
                (容量, 指纹, 校验.此刻(), 池键),
            )
            _留痕(conn, "调整池容量", 池键, 说明文字)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return 容量实况(池键)


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


# ---------------------------------------------------------------------------
# 容量闸口与两册
# ---------------------------------------------------------------------------

def 切流列表(池键: str | None = None) -> list[dict]:
    conn = 连接()
    try:
        if 池键:
            rows = conn.execute(
                "SELECT * FROM 容量切流账 WHERE 池键=? ORDER BY 指纹 DESC", (池键,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM 容量切流账 ORDER BY 指纹 DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def 裁决列表(池键: str | None = None) -> list[dict]:
    conn = 连接()
    try:
        if 池键:
            rows = conn.execute(
                "SELECT * FROM 容量裁决账 WHERE 池键=? ORDER BY 裁决号 DESC LIMIT 200",
                (池键,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM 容量裁决账 ORDER BY 裁决号 DESC LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def 记录裁决(裁决: dict) -> None:
    """把一次被拒裁决独立落旁路账（申领主事务已回滚，拒绝仍要留册）。"""
    conn = 连接()
    try:
        conn.execute(
            """INSERT INTO 容量裁决账
               (时刻,池键,指纹,读到容量,读到已占,可申领余量,租约号,租户,结论,原因码,详情)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                裁决.get("时刻") or 校验.此刻(),
                裁决["池键"],
                int(裁决.get("指纹") or 0),
                int(裁决["读到容量"]),
                int(裁决["读到已占"]),
                int(裁决["可申领余量"]),
                裁决.get("租约号", ""),
                裁决.get("租户", ""),
                裁决["结论"],
                裁决.get("原因码", "OK"),
                裁决.get("详情", ""),
            ),
        )
        if 裁决["结论"] == "拒绝":
            _留痕(
                conn,
                "容量闸拒绝申领",
                裁决["池键"],
                f"{裁决.get('租约号', '')} {裁决.get('原因码', '')} {裁决.get('详情', '')}".strip(),
            )
        conn.commit()
    finally:
        conn.close()


def 闸口预占(
    conn,
    池键: str,
    *,
    租约号: str = "",
    租户: str = "",
    依据指纹=None,
    允许超额: bool | None = None,
) -> dict:
    """在“同池锁 + BEGIN IMMEDIATE”事务内调用：读新容量读集合并原子占格。

    成功：在同一 conn 写一行“放行”裁决并返回裁决 dict（随主事务提交）。
    失败：抛 :class:`容量闸拒绝`，其 ``裁决`` 交给 记录裁决 在回滚后独立落册。
    """
    row = conn.execute(
        "SELECT 容量,已占,启用,容量指纹 FROM 资源池 WHERE 池键=?", (池键,)
    ).fetchone()
    if not row:
        raise ValueError("无此资源池")

    容量 = int(row["容量"])
    已占 = int(row["已占"])
    指纹 = int(row["容量指纹"] or 0)
    口径 = 容量口径(容量, 已占)
    裁决 = {
        "时刻": 校验.此刻(),
        "池键": 池键,
        "指纹": 指纹,
        "读到容量": 容量,
        "读到已占": 已占,
        "可申领余量": 口径["可申领余量"],
        "租约号": 租约号 or "",
        "租户": 租户 or "",
    }

    if not int(row["启用"]):
        裁决.update(结论="拒绝", 原因码="资源池未启用", 详情="该池当前禁用，不可申领")
        raise 容量闸拒绝("资源池未启用", 裁决)

    if 依据指纹 is not None:
        try:
            依据 = int(依据指纹)
        except (TypeError, ValueError):
            依据 = -1
        if 依据 != 指纹:
            裁决.update(
                结论="拒绝",
                原因码="容量已收紧拒回刷",
                详情=f"申领依据旧指纹{依据}，现行指纹{指纹}（容量{容量}）",
            )
            raise 容量闸拒绝(
                "容量已收紧：该申领依据的是旧容量读集合，按旧容量的裁决一律拒回刷，请刷新余量后再申领",
                裁决,
            )

    if 允许超额 is None:
        允许超额 = 说明.租账规().get("允许超额申领") == "1"

    if not 允许超额 and 已占 >= 容量:
        裁决.update(
            结论="拒绝",
            原因码="余量不足已拒",
            详情=f"现行容量{容量}，已占{已占}，可申领余量0；收紧后的新申领按新容量拦截",
        )
        raise 容量闸拒绝(
            f"余量不足已拒：现行容量{容量}、已占{已占}、可申领余量0；"
            "容量收紧后只拦新申领，收紧前既占保留不动",
            裁决,
        )

    # 原子条件更新：跨连接/跨进程竞态的最后一道闸。
    cur = conn.execute(
        "UPDATE 资源池 SET 已占=已占+1, 更新时=? "
        "WHERE 池键=? AND (?=1 OR 已占 < 容量)",
        (校验.此刻(), 池键, 1 if 允许超额 else 0),
    )
    if cur.rowcount != 1:
        裁决.update(
            结论="拒绝",
            原因码="并发余量不足已拒",
            详情="条件占格未命中，容量已被并发申领占满",
        )
        raise 容量闸拒绝("余量不足已拒：容量在并发裁决中被占满", 裁决)

    裁决.update(结论="放行", 原因码="OK", 详情=f"按现行容量{容量}放行")
    conn.execute(
        """INSERT INTO 容量裁决账
           (时刻,池键,指纹,读到容量,读到已占,可申领余量,租约号,租户,结论,原因码,详情)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            裁决["时刻"],
            池键,
            指纹,
            容量,
            已占,
            裁决["可申领余量"],
            租约号,
            租户,
            "放行",
            "OK",
            裁决["详情"],
        ),
    )
    return 裁决


def 预占一格(
    池键: str,
    租约号: str = "",
    租户: str = "",
    依据指纹=None,
) -> dict | None:
    """向后兼容的独立占格入口；新租约申领走与租约同事务的 闸口预占。"""
    池键 = 校验.池键(池键)
    with 池锁(池键):
        conn = 连接()
        conn.isolation_level = None
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                裁决 = 闸口预占(
                    conn, 池键, 租约号=租约号, 租户=租户, 依据指纹=依据指纹
                )
            except 容量闸拒绝 as e:
                conn.rollback()
                记录裁决(e.裁决)
                raise
            conn.commit()
            return 裁决
        finally:
            conn.close()


def 释放一格(池键: str) -> None:
    if not 池键:
        return
    with 池锁(池键):
        conn = 连接()
        try:
            if not conn.execute(
                "SELECT 1 FROM 资源池 WHERE 池键=?", (池键,)
            ).fetchone():
                return
            # 原子自减，避免读—改—写覆盖并发占格。
            conn.execute(
                "UPDATE 资源池 SET 已占 = MAX(0, 已占 - 1), 更新时=? WHERE 池键=?",
                (校验.此刻(), 池键),
            )
            conn.commit()
        finally:
            conn.close()
