"""L2 互斥与 dry-run 测试（P3 Step 3-3 实现；回滚快照行为待补）。"""

import pytest

import actuate.l2_mutex as l2


def test_dry_run_zero_write():
    mode, echoed = l2.actuate({"pl1_w": 40}, dry_run=True)
    assert mode == "dry-run"
    assert echoed == {"pl1_w": 40}


def test_live_refused_before_gate():
    with pytest.raises(RuntimeError):
        l2.actuate({"pl1_w": 40}, dry_run=False)


@pytest.mark.skip(reason="P3 Step 3-3 未实现：15s 超时回滚上一快照")
def test_timeout_rollback():
    pass
