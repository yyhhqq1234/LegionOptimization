"""L3 四 shield 阈值与仲裁（P3 Step 3-4 实现；阈值见 configs/fence_thresholds_v1.0.yaml）。

数值来源 docs/safety-fence-spec.md v1.0 §1–§2；运行时温度一律相对
MSR IA32_TEMPERATURE_TARGET (0x1A2) 探测的 TJMax 偏移，禁止硬编码。
"""

FENCE_VERSION = "1.0"

# 仲裁优先级（高→低，绝对优先，不可反转；围栏 §0.2）。
ARBITRATION_PRIORITY = ("temperature", "acdc", "power_cap", "fluency", "burst")

# 温度阈值（Arrow Lake-HX 基准，CPU 域取 Package/最热 P-core 较高者）。
TEMP_WARN_CPU = 90
TEMP_L1_CPU = 95
TEMP_L2_CPU = 98
TEMP_L3_CPU = 100
TEMP_WARN_GPU = 80
TEMP_L1_GPU = 85
TEMP_L2_GPU = 88
TEMP_L3_GPU = 90
# DC 模式阈值偏移（散热与功耗余量更小）。
DC_TEMP_OFFSET = -2

# 去抖 / 迟滞：连续 N 采样确认；解除需回落迟滞带下持续 T_hold。
DEBOUNCE_N = 3
TEMP_HOLD_S = 30
FLUENCY_HOLD_S = 10

# 否决码（与 BlackBox shield_verdict 回写对齐；围栏 E1-5）。
DENY_CODES = ("TEMP", "SMOOTH", "BURST_EMPTY", "AC_LOST", "MANUAL_PIN")


def judge(state48, action_raw):
    """围栏裁决；P3 Step 3-4 未实现。"""
    raise NotImplementedError("P3 Step 3-4 未实现")
