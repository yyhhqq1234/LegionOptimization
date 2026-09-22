"""Temp shield tests (fence 1; P3 Step 3-4)."""

import yaml
from pathlib import Path

import guard.shields as s

ROOT = Path(__file__).resolve().parent.parent


def _fence():
    return yaml.safe_load((ROOT / "configs" / "fence_thresholds_v1.0.yaml").read_text(encoding="utf-8"))


def test_threshold_ladder_cpu():
    assert s.TEMP_WARN_CPU < s.TEMP_L1_CPU < s.TEMP_L2_CPU < s.TEMP_L3_CPU
    assert (s.TEMP_WARN_CPU, s.TEMP_L1_CPU, s.TEMP_L2_CPU, s.TEMP_L3_CPU) == (90, 95, 98, 100)


def test_threshold_ladder_gpu():
    assert (s.TEMP_WARN_GPU, s.TEMP_L1_GPU, s.TEMP_L2_GPU, s.TEMP_L3_GPU) == (80, 85, 88, 90)


def test_dc_offset_and_debounce():
    assert s.DC_TEMP_OFFSET == -2
    assert s.DEBOUNCE_N == 3
    assert s.TEMP_HOLD_S == 30


def test_yaml_matches_code():
    f = _fence()["temperature"]
    assert (f["warn_cpu"], f["l1_cpu"], f["l2_cpu"], f["l3_cpu"]) == \
        (s.TEMP_WARN_CPU, s.TEMP_L1_CPU, s.TEMP_L2_CPU, s.TEMP_L3_CPU)
    assert f["dc_offset"] == s.DC_TEMP_OFFSET


def test_l1_soft_clip():
    out = s.l1_clip_action({"pl1_w": 40, "freq_ghz": 4.8})
    assert out["pl1_w"] == 25.0 and abs(out["freq_ghz"] - 4.6) < 1e-9
    assert out["burst_allowed"] == 0 and out["deny"] == "TEMP"
    assert s.debounce_trigger(2) is False and s.debounce_trigger(3) is True


def test_l2_trip_and_rearm():
    overall, _, _ = s.temp_level(99, 70)
    assert overall == "L2"
    trip = s.l2_trip_action()
    assert trip["pl1_w"] == 25 and trip["policy_paused"] is True
    assert s.rearm_ok(75, 65, 30) is True
    assert s.rearm_ok(85, 65, 60) is False
    assert s.rearm_ok(75, 65, 10) is False


def test_l3_critical_fallback():
    overall, _, _ = s.temp_level(101, 70)
    assert overall == "L3"
    fb = s.l3_fallback_action()
    assert fb["policy_bypassed"] is True and fb["fallback"] == "quiet.bat-equivalent"


def test_stale_conservative():
    v = s.stale_conservative(True)
    assert v["level"] == "L2" and v["conservative"] is True
    assert v["action"]["pl1_w"] == 25
    v2 = s.stale_conservative(False)
    assert v2["level"] == "OK"
