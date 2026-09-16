"""回放测试（P3 Step 3-4 门禁：B0–B2 历史 log + P1 探针 log，L2+ 误放行 = 0）。

输入 log 缺失（P1 探针待执行），行为体随 P3 Step 3-4 实现。
"""

import pytest


@pytest.mark.skip(reason="待 P1 探针 log + P3 judge 实现")
def test_replay_no_l2_false_pass():
    pass
