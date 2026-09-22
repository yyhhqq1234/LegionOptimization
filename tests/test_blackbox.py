"""BlackBox tests (fence 5.5; P3 Step 3-2)."""

import pytest

import blackbox.log as b


def _rec(**kw):
    base = {
        "policy_ver": "stub-1", "fence_ver": "1.0", "envelope_ver": "1.0",
        "state_hash": "abc", "action_raw": {"gear": "Balance"},
        "shield_verdict": {"level": "OK"}, "setpoints_final": {"pl1_w": 40},
        "temps": {"cpu": 70}, "power": {"pl1_w": 40}, "acdc": "AC",
        "burst_bucket": {"tokens_j": 700}, "fluency_stats": {"p95": 10},
    }
    base.update(kw)
    return base


def test_required_fields():
    assert set(b.REQUIRED_FIELDS) == {
        "policy_ver", "fence_ver", "envelope_ver", "state_hash", "action_raw",
        "shield_verdict", "setpoints_final", "temps", "power", "acdc",
        "burst_bucket", "fluency_stats",
    }


def test_append_and_replay():
    b.clear()
    with pytest.raises(ValueError):
        b.append({"policy_ver": "x"})
    i0 = b.append(_rec(policy_ver="stub-1"))
    i1 = b.append(_rec(policy_ver="stub-2", fence_ver="1.0"))
    assert (i1 - i0) == 1
    assert b.get(i0)["policy_ver"] == "stub-1"
    assert len(b.replay(policy_ver="stub-1")) == 1
    assert len(b.replay(fence_ver="1.0")) == 2
    ok, total = b.completeness(b.replay())
    assert total == 2 and ok == 2
    b.clear()
