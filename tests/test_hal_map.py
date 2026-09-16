"""HAL_MAP 换算测试（P3 Step 3-3 实现）。"""

import pytest

import actuate.hal_map as h


def test_map_version_and_scale():
    assert h.HAL_MAP_VERSION == "1.0"
    assert h.UV_MV_TO_CODE_SCALE == 1.024
    assert len(h.GEAR_ORDER) == 4


@pytest.mark.skip(reason="P3 Step 3-3 未实现：UV/PL/频墙换算单调性")
def test_conversion_monotonic():
    pass
