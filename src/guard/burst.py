"""Burst 令牌桶会计（围栏 §3；P3 Step 3-4 实现）。

设计意图：满桶换一次标准 burst，如 Balance (65-40)W×28s=700J=0.70kJ。
"""

# 档位 → 持续包络 PL1 / burst 上限 / 单次上限 / 桶容量 / 补充速率 / 最小间隔。
BURST_TABLE = {
    "Quiet": {"p_sustained_w": 25, "p_burst_max_w": 40, "tmax_s": 10,
              "capacity_kj": 0.15, "refill_w": 3, "gap_s": 60},
    "Balance": {"p_sustained_w": 40, "p_burst_max_w": 65, "tmax_s": 28,
                "capacity_kj": 0.70, "refill_w": 5, "gap_s": 45},
    "Beast": {"p_sustained_w": 65, "p_burst_max_w": 95, "tmax_s": 20,
              "capacity_kj": 0.60, "refill_w": 8, "gap_s": 60},
    "Extreme": {"p_sustained_w": 65, "p_burst_max_w": 110, "tmax_s": 15,
                "capacity_kj": 0.675, "refill_w": 10, "gap_s": 90},
}
SAFETY_FACTOR = 1.2  # 批准条件：余量 > 预估能量 × 系数


def update_bucket(bucket, power_w, dt_s, gear):
    """令牌桶记账；P3 Step 3-4 未实现。"""
    raise NotImplementedError("P3 Step 3-4 未实现")
