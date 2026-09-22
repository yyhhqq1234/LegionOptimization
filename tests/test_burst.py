"""Burst bucket tests (fence 3; P3 Step 3-4)."""

import guard.burst as b


def test_table_gears():
    assert set(b.BURST_TABLE) == {"Quiet", "Balance", "Beast", "Extreme"}


def test_balance_full_bucket_single_burst():
    row = b.BURST_TABLE["Balance"]
    energy_j = (row["p_burst_max_w"] - row["p_sustained_w"]) * row["tmax_s"]
    assert energy_j == 700
    assert row["capacity_kj"] * 1000 == 700


def test_safety_factor():
    assert b.SAFETY_FACTOR == 1.2


def test_bucket_accounting():
    bucket = b.new_bucket("Balance")
    assert bucket["tokens_j"] == 700.0
    b2 = b.update_bucket(bucket, 20, 10, "Balance", temp_ok=True, now_s=0.0)
    assert b2["tokens_j"] == 700.0
    b3 = b.update_bucket(bucket, 65, 10, "Balance", temp_ok=True, now_s=0.0)
    assert b3["tokens_j"] == 450.0
    b4 = b.update_bucket({"gear": "Balance", "tokens_j": 100.0, "frozen_until_s": 0.0,
                          "empty_strikes": 0, "last_burst_s": 0.0},
                         20, 10, "Balance", temp_ok=False, now_s=0.0)
    assert b4["tokens_j"] == 100.0
    assert b.can_burst(bucket, 500, "Balance", temp_ok=True, now_s=0.0) is True
    assert b.can_burst(bucket, 600, "Balance", temp_ok=True, now_s=0.0) is False
    assert b.can_burst(bucket, 100, "Balance", temp_ok=False, now_s=0.0) is False


def test_violation_and_freeze():
    assert b.check_tmax_violation(29, "Balance") is True
    assert b.check_tmax_violation(28, "Balance") is False
    bucket = b.new_bucket("Balance", tokens_j=0.0)
    now = 100.0
    bucket = b.note_empty_request(bucket, now)
    bucket = b.note_empty_request(bucket, now + 1)
    assert bucket["frozen_until_s"] == 0.0
    bucket = b.note_empty_request(bucket, now + 2)
    assert bucket["frozen_until_s"] == now + 2 + 300.0
    assert b.can_burst(bucket, 10, "Balance", temp_ok=True, now_s=now + 3) is False
