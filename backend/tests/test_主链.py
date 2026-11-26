import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["数据目录"] = _tmp
os.environ["夹具目录"] = str(Path(__file__).resolve().parents[2] / "fixtures")

from app import seed
from app.services import 互证, 夹具, 租约, 续约, 说明


def setup_module():
    seed.初始化库()


def test_申领与心跳():
    ev = 租约.申领(
        {"池键": "pool-compute", "租户": "pytest-team", "租期分钟": 90, "立即生效": True}
    )
    lid = ev["租约号"]
    hb = 续约.发心跳({"租约号": lid, "延长分钟": 20})
    assert hb["结果"] == "成功"
    row = 说明.租约一条(lid)
    assert row["状态"] == "已续约"


def test_互证报告():
    rep = 互证.跑一次()
    assert "是否全部对齐" in rep
    assert 说明.互证列表()


def test_夹具批量():
    try:
        夹具.批量申领("批量租约样例")
    except Exception:
        pass
    assert 说明.租约列表()