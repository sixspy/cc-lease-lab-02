# -*- coding: utf-8 -*-
"""测容量切流乙（租账互证服务 / 读集合分叉）。

收紧到 60 后，收紧前既占、超过新容量的那部分是“旧容量影子占用”：
它们作为已生效租约继续保留，但绝不能被互证误标成“新容量下的合法占用”。

基线红因：旧 ``互证.跑一次`` 只核对 ``SUM(资源池.已占)`` 与未回收租约数，
两者在干净夹具里恰好相等 → 判“全部对齐”，对 已占61 > 容量60 视而不见，
等于把 1 格旧容量影子占用误标成新容量 60 内的合法占用。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import db, seed
from app.services import 互证, 资源, 租约, 说明

KEY = "pool-shadow-b"
CAP = 60
USED = 61  # 60 格新容量内合法 + 1 格旧容量影子

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture()
def iso_db(tmp_path, monkeypatch):
    _orig_connect = sqlite3.connect

    def _fast_connect(*a, **k):
        c = _orig_connect(*a, **k)
        c.execute("PRAGMA synchronous=OFF")
        c.execute("PRAGMA busy_timeout=15000")
        return c

    monkeypatch.setattr(sqlite3, "connect", _fast_connect)
    monkeypatch.setattr(db, "数据目录", tmp_path)
    monkeypatch.setattr(db, "库路径", tmp_path / "乙.db")
    conn = db.连接()
    try:
        conn.executescript(seed.建表)
        conn.commit()
    finally:
        conn.close()
    yield tmp_path


def _造一致的超容占用():
    资源.登记({"池键": KEY, "名称": "影子占用乙池", "容量": 100})
    for i in range(USED):
        租约.申领(
            {
                "池键": KEY,
                "租户": f"shadow-{i % 4}",
                "租约号": f"ls-pre-b-{i:03d}",
                "租期分钟": 60,
                "立即生效": True,
            }
        )
    # 用只读归档式 setup 直接把现行容量收到 60，单独考验互证口径
    # （不经过 资源.改容量，以免与甲的收紧策略耦合）。
    c = db.连接()
    try:
        c.execute("UPDATE 资源池 SET 容量=? WHERE 池键=?", (CAP, KEY))
        c.commit()
    finally:
        c.close()
    row = 资源.一条(KEY)
    assert row["容量"] == CAP and row["已占"] == USED


def test_乙_互证不得把旧容量影子占用误标为新容量合法占用(iso_db):
    _造一致的超容占用()

    rep = 互证.跑一次()

    # —— 首要见红断言：基线会把它判成“对齐” ——
    assert rep["是否全部对齐"] is False, (
        "互证把旧容量影子占用误标成新容量下的合法占用："
        f"已占 {USED} > 现行容量 {CAP}，却判 aligned={rep['是否全部对齐']}，"
        f"摘要={rep['差异摘要']}"
    )

    # —— 新容量 / 旧容量影子 必须分轨口径 ——
    assert int(rep.get("旧容量影子占用合计", -1)) == USED - CAP
    assert int(rep.get("新容量内合法占用合计", -1)) == CAP
    over = rep.get("容量超容池") or []
    assert any(
        x.get("池键") == KEY and int(x.get("影子占用")) == USED - CAP
        for x in over
    ), f"未见该池影子占用明细：{over}"
    assert "影子" in rep["差异摘要"]

    # —— 落库报告同样不得标对齐 ——
    rows = 说明.互证列表()
    latest = rows[0]
    assert int(latest["是否对齐"]) == 0
    assert "影子" in (latest["差异摘要"] or "")
