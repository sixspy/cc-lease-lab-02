from __future__ import annotations

import json
from pathlib import Path

from app.db import 夹具目录
from app.services import 租约


def 列表() -> list:
    if not 夹具目录.is_dir():
        return []
    out = []
    for p in sorted(夹具目录.glob("*.json")):
        out.append({"名称": p.stem, "文件": p.name})
    return out


def 读取(name: str) -> dict:
    路径 = 夹具目录 / f"{name}.json"
    if not 路径.is_file():
        路径 = 夹具目录 / name
    if not 路径.is_file():
        raise FileNotFoundError(name)
    return json.loads(路径.read_text(encoding="utf-8"))


def 批量申领(name: str) -> list:
    体 = 读取(name)
    out = []
    for item in 体.get("租约", []):
        out.append(租约.申领(item))
    return out