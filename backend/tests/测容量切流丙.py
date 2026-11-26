# -*- coding: utf-8 -*-
"""测容量切流丙（争用：两名操作员同时改同一池容量并抢申领）。

不加锁时“先读 已占/容量 → Python 判余量 → 无条件 已占=已占+1”是 TOCTOU：
两侧都读到最后一格尚空，于是双成功、各留一行超额，占用数与容量设置不符。

本文件用一个“放慢租账规读取”的时序探针，把基线那道读—判—写窗口稳定撑开
（基线 8/8 轮双成功）；加锁 + 原子条件更新后，同一池串行裁决，恰好放一格。
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from app import db, seed
from app.services import 说明, 资源, 租约

KEY = "pool-race-c"
CAP = 60
USED_BEFORE_RACE = 59  # 只剩一格

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
    monkeypatch.setattr(db, "库路径", tmp_path / "丙.db")
    conn = db.连接()
    try:
        conn.executescript(seed.建表)
        conn.commit()
    finally:
        conn.close()
    yield tmp_path


def _种到边界(monkeypatch, key=KEY, cap=CAP, used=USED_BEFORE_RACE):
    资源.登记({"池键": key, "名称": "争用丙池", "容量": cap})
    now = "2026-11-26T00:00:00Z"
    c = db.连接()
    try:
        rows = [
            (f"ls-pre-c-{i:03d}", key, "t", "生效中", now, now, "2099-01-01T00:00:00Z", now)
            for i in range(used)
        ]
        c.executemany(
            """INSERT INTO 租约(租约号,池键,租户,状态,申领时,生效时,到期时刻,更新时)
               VALUES (?,?,?,?,?,?,?,?)""",
            rows,
        )
        c.execute("UPDATE 资源池 SET 已占=? WHERE 池键=?", (used, key))
        c.commit()
    finally:
        c.close()

    # 撑开基线“读到旧占用之后、判定之前”的窗口；对加锁实现无害（仅增延时）。
    _orig = 说明.租账规

    def _slow():
        time.sleep(0.05)
        return _orig()

    monkeypatch.setattr(说明, "租账规", _slow)


def _并发申领(key, n, prefix):
    bar = threading.Barrier(n)
    ok, rej, errs = [], [], []
    lk = threading.Lock()

    def worker(j):
        bar.wait()
        try:
            r = 租约.申领(
                {"池键": key, "租户": "race", "租约号": f"{prefix}-{j:03d}", "租期分钟": 60}
            )
            with lk:
                ok.append(r["租约号"])
        except Exception as e:  # 容量闸拒绝 / 其他 ValueError 都算未放行
            with lk:
                if "容量" in str(e) or "满" in str(e) or "余量" in str(e) or "收紧" in str(e):
                    rej.append(str(e))
                else:
                    errs.append(repr(e))

    ts = [threading.Thread(target=worker, args=(j,)) for j in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    return ok, rej, errs


def test_丙_两侧抢最后一格_不得双成功各留超额(iso_db, monkeypatch):
    _种到边界(monkeypatch)

    ok, rej, errs = _并发申领(KEY, 2, "ls-race-two")

    assert not errs, f"出现非预期错误：{errs}"
    assert len(ok) == 1, (
        "两名操作员同时抢同一池最后一格，不加锁双成功、各留一行超额："
        f"成功 {len(ok)} 拒 {len(rej)}"
    )
    row = 资源.一条(KEY)
    assert int(row["已占"]) == CAP, f"占用数互相覆盖/超卖：已占={row['已占']} 容量={CAP}"
    live = db.连接().execute(
        "SELECT COUNT(*) FROM 租约 WHERE 池键=? AND 状态 IN ('生效中','已续约','待生效')",
        (KEY,),
    ).fetchone()[0]
    assert live == CAP and int(row["已占"]) == live, "池已占必须与租约行数账实相符"

    # 双写两轨：这一抢必须留下一行放行、一行拒绝的容量裁决（旁路账册）。
    if callable(getattr(资源, "裁决列表", None)):
        vs = 资源.裁决列表(KEY)
        assert sum(1 for v in vs if v["结论"] == "放行") >= 1
        assert any(v["结论"] == "拒绝" for v in vs), "失败一侧未落拒绝裁决"


def test_丙_十六路并发仅放一格且绝不超卖(iso_db, monkeypatch):
    _种到边界(monkeypatch)
    ok, rej, errs = _并发申领(KEY, 16, "ls-race-fan")
    assert not errs, f"并发出现非预期错误：{errs[:3]}"
    assert len(ok) == 1, f"最后一格应只放 1 行，实际放了 {len(ok)} 行"
    assert len(rej) == 15
    row = 资源.一条(KEY)
    assert int(row["已占"]) <= CAP
    assert int(row["已占"]) == CAP


def test_丙_同池容量锁与指纹切流账_双写两轨(iso_db, monkeypatch):
    # 同一池必须拿到同一把容量锁（双会话抢的就是它）。
    assert callable(getattr(资源, "池锁", None)), "资源服务缺少按池容量锁"
    assert 资源.池锁(KEY) is 资源.池锁(KEY)

    资源.登记({"池键": "pool-fp", "名称": "指纹池", "容量": 100})
    row = 资源.改容量("pool-fp", 60)
    assert int(row["容量"]) == 60
    assert int(row.get("容量指纹", 0)) >= 1

    # 指纹先落入切流账册，旧容量100 -> 新容量60 可查。
    rows = 资源.切流列表("pool-fp")
    assert rows and int(rows[-1]["旧容量"]) == 100 and int(rows[-1]["新容量"]) == 60

    # 成败双写：一次放行 + 一次拒绝各落一条容量裁决（旁路），主账留痕也在。
    租约.申领({"池键": "pool-fp", "租户": "ok", "租约号": "ls-fp-1", "租期分钟": 60})
    now = "2026-11-26T00:00:00Z"
    c = db.连接()
    try:
        c.executemany(
            """INSERT INTO 租约(租约号,池键,租户,状态,申领时,生效时,到期时刻,更新时)
               VALUES (?,?,?,'生效中',?,?,?,?)""",
            [
                (f"ls-fp-fill-{i:03d}", "pool-fp", "fill", now, now, "2099-01-01T00:00:00Z", now)
                for i in range(59)  # 已有 ls-fp-1，再补 59 => 60 格满
            ],
        )
        c.execute("UPDATE 资源池 SET 已占=60 WHERE 池键='pool-fp'")
        c.commit()
    finally:
        c.close()

    with pytest.raises(Exception):
        租约.申领({"池键": "pool-fp", "租户": "over", "租约号": "ls-fp-over", "租期分钟": 60})
    assert int(资源.一条("pool-fp")["已占"]) == 60
    vs = 资源.裁决列表("pool-fp")
    assert any(v["结论"] == "放行" for v in vs)
    assert any(v["结论"] == "拒绝" for v in vs)
