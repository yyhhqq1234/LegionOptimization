"""BlackBox 结构化日志（围栏 §5.5；P3 Step 3-2 实现）。

每决策记录：三版本号联合标注；复现要求：给定三版本 + log 可重放裁决。
"""

# §5.5 必填字段（缺一即日志不完整，canary 期要求完整率 100%）。
REQUIRED_FIELDS = (
    "policy_ver", "fence_ver", "envelope_ver", "state_hash", "action_raw",
    "shield_verdict", "setpoints_final", "temps", "power", "acdc",
    "burst_bucket", "fluency_stats",
)


def append(record):
    """追加一条决策记录；P3 Step 3-2 未实现。"""
    raise NotImplementedError("P3 Step 3-2 未实现")
