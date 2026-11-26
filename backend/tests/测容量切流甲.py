# -*- coding: utf-8 -*-
"""测容量切流甲（资源服务 / 容量口）。

骨签：容量由一百收紧到六十后，收紧后的“新申领”必须按新容量拦截；
收紧前已生效的租约不得被静默挤掉。

复现载体：夹具键「超额申领甲」。

基线红因：预置已占 61（>60）时，旧 ``资源.改容量`` 以
“容量不能低于当前已占”拒收收紧，容量仍停在 100；于是夹具里收紧后的
超额新申领被“按一百”放行——正是“容量已收到六十仍按一百放行新申领”。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import db, seed
from app.services import 夹具, 资源, 租约

KEY = "pool-over-a"
OLD_CAP = 100
NEW_CAP = 60
PREFILL = 61  # >60：在旧容量100下合法，在新容量60下产生1格旧容量影子占用

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture()
def iso_db(tmp_path, monkeypatch):
    # 仅测试提速：本环境 fsync 极慢。关掉同步刷盘不改变锁/事务/TOCTOU 语义。
    _orig_connect = sqlite3.connect

    def _fast_connect(*a, **k):
        c = _orig_connect(*a, **k)
        c.execute("PRAGMA synchronous=OFF")
        c.execute("PRAGMA busy_timeout=15000")
        return c

    monkeypatch.setattr(sqlite3, "connect", _fast_connect)
    monkeypatch.setattr(db, "数据目录", tmp_path)
    monkeypatch.setattr(db, "库路径", tmp_path / "甲.db")
    monkeypatch.setattr(夹具, "夹具目录", FIXTURE_DIR)
    conn = db.连接()
    try:
        conn.executescript(seed.建表)
        conn.commit()
    finally:
        conn.close()
    yield tmp_path


def _预置旧容量占用():
    资源.登记({"池键": KEY, "名称": "超额申领甲池", "容量": OLD_CAP})
    for i in range(PREFILL):
        租约.申领(
            {
                "池键": KEY,
                "租户": f"old-{i % 5}",
                "租约号": f"ls-pre-a-{i:03d}",
                "租期分钟": 60,
                "立即生效": True,
            }
        )
    row = 资源.一条(KEY)
    assert row["容量"] == OLD_CAP and row["已占"] == PREFILL


def test_甲_收紧到六十后夹具超额申领必须按新容量拒(iso_db):
    _预置旧容量占用()

    # 人在资源池页把额定容量 100 -> 60 并保存。
    cap_error = None
    cap_row = None
    try:
        cap_row = 资源.改容量(KEY, NEW_CAP)
    except Exception as e:  # 基线会在这里抛“容量不能低于当前已占”
        cap_error = e

    # —— 首要骨签（放在最前断言，使基线以“仍按一百放行”字面见红）——
    before = 资源.一条(KEY)["已占"]
    leaked = False
    leaked_rows = []
    try:
        out = 夹具.批量申领("超额申领甲")
        leaked = True
        leaked_rows = out
    except Exception:
        leaked = False

    assert leaked is False, (
        "容量已收到六十仍按一百放行新申领："
        f"夹具「超额申领甲」的收紧后新申领被放行 {len(leaked_rows)} 行"
        f"（cap_error={cap_error}）"
    )
    after = 资源.一条(KEY)["已占"]
    assert after == before, f"被拒申领不得抬升已占：before={before} after={after}"

    # —— 新容量契约：收紧本身必须当场生效并重算可申领余量 ——
    assert cap_error is None, f"收紧保存不应被旧占用挡住：{cap_error}"
    assert int(cap_row["容量"]) == NEW_CAP
    实况 = 资源.容量实况(KEY) if hasattr(资源, "容量实况") else cap_row
    assert int(实况["可申领余量"]) == 0
    assert int(实况.get("影子占用", 0)) == PREFILL - NEW_CAP

    # —— 已生效租约一根毫毛不动 ——
    live = db.连接().execute(
        "SELECT COUNT(*) FROM 租约 WHERE 池键=? AND 状态 IN ('生效中','已续约')",
        (KEY,),
    ).fetchone()[0]
    assert live == PREFILL, "收紧容量不得静默挤掉已生效租约"

    # —— 成败要落容量裁决账（旁路），供租约台旁写出 ——
    if hasattr(资源, "裁决列表"):
        verdicts = 资源.裁决列表(KEY)
        assert any(v["结论"] == "拒绝" for v in verdicts), "未见拒绝裁决入账"
