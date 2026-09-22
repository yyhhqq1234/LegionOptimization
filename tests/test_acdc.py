"""ACDC tests (fence 4; P3 Step 3-4)."""

import guard.acdc as a


def test_dc_envelope_order():
    assert a.DC_TABLE["DC-1"]["pl1_w"] == 35
    assert a.DC_TABLE["DC-2"]["pl1_w"] == 25
    assert a.DC_TABLE["DC-3"]["pl1_w"] == 15


def test_timing_contract():
    assert a.ACDC_FALLBACK_S == 1
    assert a.AC_REARM_STABLE_S == 2


def test_acdc_fallback_landing():
    act = a.on_power_event({"type": "AC_LOST", "soc_pct": 70}, history=[], now_s=0.0)
    assert act["target_dc"] == "DC-1" and act["burst_terminate"] is True
    assert act["deadline_s"] == 1 and act["deny"] == "AC_LOST"
    assert act["setpoints"] == {"pl1_w": 35, "freq_ghz": 4.2}
    act2 = a.on_power_event({"type": "UNKNOWN", "soc_pct": 10}, history=[], now_s=0.0)
    assert act2["target_dc"] == "DC-3"
    assert a.select_dc_gear(10) == "DC-3" and a.select_dc_gear(30) == "DC-2"


def test_replug_ramp_and_flap_lock():
    act = a.on_power_event({"type": "AC_RESTORED", "soc_pct": 50}, history=[], now_s=10.0, ac_stable_s=1.0)
    assert act["ramp"] == [] and act["reason"] == "wait-2s-stable"
    act2 = a.on_power_event({"type": "AC_RESTORED", "soc_pct": 50}, history=[], now_s=10.0, ac_stable_s=2.5)
    assert act2["ramp"][-1] == "AC" and "DC-2" in act2["ramp"]
    hist = [(0.0, True), (10.0, False), (20.0, True), (30.0, False)]
    act3 = a.on_power_event({"type": "AC_LOST", "soc_pct": 80}, history=hist, now_s=40.0)
    assert act3["flap_lock"] is True and act3["target_dc"] == "DC-2"
    assert act3["flap_lock_s"] == 1800
