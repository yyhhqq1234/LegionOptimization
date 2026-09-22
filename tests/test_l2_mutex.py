"""L2 mutex tests (P3 Step 3-3)."""

import pytest

import actuate.l2_mutex as l2


def test_dry_run_zero_write():
    mode, echoed = l2.actuate({"pl1_w": 40}, dry_run=True)
    assert mode == "dry-run"
    assert echoed == {"pl1_w": 40}


def test_live_refused_before_gate():
    with pytest.raises(RuntimeError):
        l2.actuate({"pl1_w": 40}, dry_run=False)


def test_timeout_rollback():
    snap = {"pl1_w": 40, "freq_ghz": 4.8}
    res, restored, err = l2.transact(lambda: "ok", snap, elapsed_s=1.0)
    assert res == "ok" and restored is None and err is None
    res2, restored2, err2 = l2.transact(lambda: "ok", snap, elapsed_s=16.0)
    assert res2 is None and restored2 == snap and isinstance(err2, TimeoutError)

    def _boom():
        raise ValueError("boom")

    res3, restored3, err3 = l2.transact(_boom, snap, elapsed_s=0.5)
    assert res3 is None and restored3 == snap and isinstance(err3, ValueError)
    mode, data, errx = l2.try_actuate_with_timeout(snap, lambda: "ok", elapsed_s=20.0, dry_run=True)
    assert mode == "dry-run-rollback" and data == snap and isinstance(errx, TimeoutError)
