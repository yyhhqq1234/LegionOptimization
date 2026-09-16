"""温度 Shield 单元测试（围栏 §1；行为体 P3 Step 3-4 实现）。"""

import pytest
import yaml
from pathlib import Path

import guard.shields as s

ROOT = Path(__file__).resolve().parent.parent


def _fence():
    return yaml.safe_load((ROOT / "configs" / "fence_thresholds_v1.0.yaml").read_text(encoding="utf-8"))


def test_threshold_ladder_cpu():
    assert s.TEMP_WARN_CPU < s.TEMP_L1_CPU < s.TEMP_L2_CPU < s.TEMP_L3_CPU
    assert (s.TEMP_WARN_CPU, s.TEMP_L1_CPU, s.TEMP_L2_CPU, s.TEMP_L3_CPU) == (90, 95, 98, 100)


def test_threshold_ladder_gpu():
    assert (s.TEMP_WARN_GPU, s.TEMP_L1_GPU, s.TEMP_L2_GPU, s.TEMP_L3_GPU) == (80, 85, 88, 90)


def test_dc_offset_and_debounce():
    assert s.DC_TEMP_OFFSET == -2
    assert s.DEBOUNCE_N == 3
    assert s.TEMP_HOLD_S == 30


def test_yaml_matches_code():
    f = _fence()["temperature"]
    assert (f["warn_cpu"], f["l1_cpu"], f["l2_cpu"], f["l3_cpu"]) == \
        (s.TEMP_WARN_CPU, s.TEMP_L1_CPU, s.TEMP_L2_CPU, s.TEMP_L3_CPU)
    assert f["dc_offset"] == s.DC_TEMP_OFFSET


@pytest.mark.skip(reason="P3 Step 3-4 未实现：L1 软裁剪行为")
def test_l1_soft_clip():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：L2 跳闸 + 策略暂停 + 重武装")
def test_l2_trip_and_rearm():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：L3 临界回退")
def test_l3_critical_fallback():
    pass


@pytest.mark.skip(reason="P3 Step 3-4 未实现：stale/野值按保守假设")
def test_stale_conservative():
    pass
