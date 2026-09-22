"""Arbitration tests (fence 0.2; P3 Step 3-4)."""

import guard.shields as s


def test_priority_order():
    assert s.ARBITRATION_PRIORITY == ("temperature", "acdc", "power_cap", "fluency", "burst")
    assert s.ARBITRATION_PRIORITY[0] == "temperature"
    assert s.ARBITRATION_PRIORITY[-1] == "burst"


def test_multi_trigger_union():
    out = s.arbitrate([("fluency", 1, "p95"), ("temperature", 3, "L2"), ("burst", 0, "ok")])
    assert out["winner"] == "temperature" and out["level_rank"] == 3
    assert set(out["all_sources"]) == {"fluency", "temperature", "burst"}
    assert s.arbitrate([])["winner"] is None
    v = s.judge({"cpu_c": 96, "gpu_c": 70}, {"pl1_w": 40, "freq_ghz": 4.8})
    assert v["level"] == "L1" and v["deny"] == "TEMP"
