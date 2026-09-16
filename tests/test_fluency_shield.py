"""流畅 Shield 单元测试（围栏 §2；行为体 P3 Step 3-4 实现）。"""

import pytest

import guard.shields as s


def test_hold_and_deny_code():
    assert s.FLUENCY_HOLD_S == 10
    assert "SMOOTH" in s.DENY_CODES


@pytest.mark.skip(reason="P3 Step 3-4 未实现：p95/1%Low/jank 触发判据")
def test_trigger_criteria():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：hold 期 + 单调上调一档")
def test_hold_and_single_step_up():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：无帧数据静默 + 切场抑制")
def test_silent_and_suppress():
    pass
