"""L4 策略 stub（P3 采集用；P4 接代理模型，P6 接离线 RL 策略）。"""

from actuate.hal_map import GEAR_ORDER


def suggest(state48):
    """返回静态包络建议（dry-run 下供采集链路联调，不做任何下发）。"""
    return {"gear_desired": GEAR_ORDER[1], "source": "static-stub"}
