import os
import sqlite3
from pathlib import Path

数据目录 = Path(os.environ.get("数据目录", Path(__file__).resolve().parent.parent / "data"))
夹具目录 = Path(os.environ.get("夹具目录", Path(__file__).resolve().parent.parent.parent / "fixtures"))
库路径 = 数据目录 / "租约台.db"


def 连接() -> sqlite3.Connection:
    数据目录.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(库路径, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn