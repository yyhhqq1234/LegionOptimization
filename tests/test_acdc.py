"""拔电回退单元测试（围栏 §4；行为体 P3 Step 3-4 实现）。"""

import pytest

import guard.acdc as a


def test_dc_envelope_order():
    assert a.DC_TABLE["DC-1"]["pl1_w"] == 35
    assert a.DC_TABLE["DC-2"]["pl1_w"] == 25
    assert a.DC_TABLE["DC-3"]["pl1_w"] == 15


def test_timing_contract():
    assert a.ACDC_FALLBACK_S == 1
    assert a.AC_REARM_STABLE_S == 2


@pytest.mark.skip(reason="P3 Step 3-4 未实现：AC→DC <1s 落地 + burst 终止")
def test_acdc_fallback_landing():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：回插逐档爬升 + 抖动锁定")
def test_replug_ramp_and_flap_lock():
    pass
