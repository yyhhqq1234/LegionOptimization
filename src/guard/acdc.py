"""AC→DC 拔电回退（围栏 §4；P3 Step 3-4 实现）。

状态未知按 DC 处理（保守默认）；AC→DC 立即采信，回切需稳定 2s。
"""

# DC 持续包络（与 AC 解耦；burst 默认禁用）。
DC_TABLE = {
    "DC-1": {"pl1_w": 35, "freq_ghz": 4.2, "min_soc": 60},
    "DC-2": {"pl1_w": 25, "freq_ghz": 3.8, "min_soc": 20},
    "DC-3": {"pl1_w": 15, "freq_ghz": 3.0, "min_soc": 0},
}
ACDC_FALLBACK_S = 1  # AC→DC 安全包络落地时限
AC_REARM_STABLE_S = 2  # 回切需 AC 稳定时长
AC_FLAP_WINDOW_S = 300  # 5min 内 ≥3 次翻转则锁 DC-2 30min
AC_FLAP_LOCK_S = 1800


def on_power_event(event):
    """电源事件处理；P3 Step 3-4 未实现。"""
    raise NotImplementedError("P3 Step 3-4 未实现")
