"""Burst 令牌桶单元测试（围栏 §3；行为体 P3 Step 3-4 实现）。"""

import pytest

import guard.burst as b


def test_table_gears():
    assert set(b.BURST_TABLE) == {"Quiet", "Balance", "Beast", "Extreme"}


def test_balance_full_bucket_single_burst():
    """满桶换一次标准 burst：(65-40)W×28s = 700J = 0.70kJ。"""
    row = b.BURST_TABLE["Balance"]
    energy_j = (row["p_burst_max_w"] - row["p_sustained_w"]) * row["tmax_s"]
    assert energy_j == 700
    assert row["capacity_kj"] * 1000 == 700


def test_safety_factor():
    assert b.SAFETY_FACTOR == 1.2


@pytest.mark.skip(reason="P3 Step 3-4 未实现：桶记账 refill/扣费/冻结语义")
def test_bucket_accounting():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：超 Tmax 违规 + 空桶冻结 5min")
def test_violation_and_freeze():
    pass
