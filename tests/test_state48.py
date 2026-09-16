"""State48 构建测试（P3 Step 3-2 实现）。"""

import pytest

import state.state48 as st


def test_feature_contract():
    assert st.N_FEATURES == 48
    assert st.S46_TS_INJECT_OK == 0


@pytest.mark.skip(reason="P3 Step 3-2 未实现：缺失 valid=0，禁填旧值")
def test_valid_mask_no_fill():
    pass


@pytest.mark.skip(reason="P3 Step 3-2 未实现：1Hz 构建 + 归一化")
def test_build_1hz_normalize():
    pass
