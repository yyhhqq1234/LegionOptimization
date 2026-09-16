"""L0：nvidia-smi CSV 1Hz 轮询（P1 Step 1-4 / P3 Step 3-2 实现）。"""

POLL_HZ = 1
# EGM 必需字段：利用率/频率/功率/温度/功耗墙可用性。
FIELDS = ("utilization", "clock", "power", "temperature", "power_limit")
