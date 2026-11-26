"""租约分片策略预留：按池键路由租约主副本。"""

from app.services import 说明


def 分片统计() -> dict:
    rows = 说明.资源池列表()
    return {r["池键"]: 说明.租约列表().__len__() for r in rows}