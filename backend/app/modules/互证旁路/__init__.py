"""互证旁路：只读快照概览，不写报告。"""

from app.services import 说明


def 快览() -> dict:
    o = 说明.概览()
    return {k: v for k, v in o.items() if k != "租账规"}