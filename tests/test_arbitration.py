"""仲裁优先级测试（围栏 §0.2；多触发并集 P3 Step 3-4 实现）。"""

import pytest

import guard.shields as s


def test_priority_order():
    assert s.ARBITRATION_PRIORITY == ("temperature", "acdc", "power_cap", "fluency", "burst")
    assert s.ARBITRATION_PRIORITY[0] == "temperature"
    assert s.ARBITRATION_PRIORITY[-1] == "burst"


@pytest.mark.skip(reason="P3 Step 3-4 未实现：多触发最保守并集 + 全源记录")
def test_multi_trigger_union():
    pass
