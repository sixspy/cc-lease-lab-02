"""心跳降频：连续失败时建议拉长续约间隔。"""

from app.services import 续约


def 建议间隔(租约号: str) -> int:
    fails = 续约.最近失败次数(租约号)
    if fails >= 3:
        return 300
    if fails >= 1:
        return 120
    return 60