"""L1 换算：HAL_MAP v1.0（P3 Step 3-3 实现）。

频墙→powercfg+SST/NonTurbo 对齐表；UV mV→FIVR 编码；PL→EAX/EDX 单调映射。
"""

HAL_MAP_VERSION = "1.0"
# UV 毫伏转 FIVR 编码系数（mV × 系数 → hex）。
UV_MV_TO_CODE_SCALE = 1.024
# 档位顺序（命名以 specs v1.0 为准；DC 为正交维度，不在档位轴上）。
GEAR_ORDER = ("Quiet", "Balance", "Beast", "Extreme")
