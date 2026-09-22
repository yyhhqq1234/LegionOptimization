"""Fluency shield tests (fence 2; P3 Step 3-4)."""

import guard.shields as s


def test_hold_and_deny_code():
    assert s.FLUENCY_HOLD_S == 10
    assert "SMOOTH" in s.DENY_CODES


def test_trigger_criteria():
    hit, reason = s.fluency_trigger(20, 10, low_fps=30, baseline_low_fps=60,
                                   app_class="game-fullscreen")
    assert hit is True and reason in ("p95-degraded", "low-drop")
    hit2, _ = s.fluency_trigger(10, 10, jank_n=12, app_class="game-fullscreen")
    assert hit2 is True
    hit3, _ = s.fluency_trigger(50, 10, app_class="game-fullscreen")
    assert hit3 is True


def test_hold_and_single_step_up():
    out = s.fluency_hold_action("Balance")
    assert out["gear_hold"] == "Balance" and out["gear_up"] == "Beast"
    assert out["hold_s"] == 10 and out["single_step"] is True
    top = s.fluency_hold_action("Extreme")
    assert top["gear_up"] is None


def test_silent_and_suppress():
    hit, reason = s.fluency_trigger(99, 10, has_frames=False)
    assert hit is False and reason == "silent-no-frames"
    hit2, reason2 = s.fluency_trigger(99, 10, app_class="idle-desktop")
    assert hit2 is False
    hit3, reason3 = s.fluency_trigger(99, 10, jank_n=0, app_class="game-fullscreen",
                                     since_switch_s=2.0)
    assert hit3 is False and reason3 == "suppressed-switch"
