"""脚手架冒烟：包可导入、版本对齐、铁律护栏（P3 Step 3-1）。"""

import re
import sys
from pathlib import Path

import yaml

import actuate.hal_map as hal_map
import actuate.l2_mutex as l2
import blackbox.log as blog
import guard.acdc as acdc
import guard.burst as burst
import guard.shields as shields
import policy.stub as stub
import sense.nvidia_poll as nvidia
import sense.wmi_events as wmi
import state.state48 as state48

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    return yaml.safe_load((ROOT / "configs" / name).read_text(encoding="utf-8"))


def test_python_version():
    assert sys.version_info >= (3, 12)


def test_dry_run_default_on():
    assert l2.DRY_RUN_DEFAULT is True
    assert l2.LOCK_NAME == "hal-actuation.lock"
    assert l2.TIMEOUT_S == 15


def test_state48_shape_contract():
    assert state48.N_FEATURES == 48
    assert state48.S46_TS_INJECT_OK == 0


def test_version_pinning():
    env = _load("envelope_v1.0.yaml")
    fence = _load("fence_thresholds_v1.0.yaml")
    assert hal_map.HAL_MAP_VERSION == "1.0"
    assert shields.FENCE_VERSION == "1.0"
    assert env["envelope_ver"] == "1.0"
    assert fence["fence_ver"] == "1.0"


def test_envelope_gears():
    env = _load("envelope_v1.0.yaml")
    assert set(env["gears"]) == {"Quiet", "Balance", "Beast", "Extreme"}
    assert env["gears"]["Balance"]["pl1_w"] == 40


def test_no_g5_code_token():
    """铁律护栏：src 代码中不得出现作为档位的 G5 引用（注释提及禁词不受限）。"""
    token = re.compile(r'"G5"|\'G5\'')
    hits = [str(p) for p in (ROOT / "src").rglob("*.py")
            if token.search(p.read_text(encoding="utf-8"))]
    assert hits == []


def test_wmi_event_names():
    assert wmi.FAN_MODE_EVENT.startswith("LENOVO_GAMEZONE_")
    assert wmi.THERMAL_MODE_EVENT.startswith("LENOVO_GAMEZONE_")


def test_nvidia_poll_baseline():
    assert nvidia.POLL_HZ == 1
    assert "power" in nvidia.FIELDS and "temperature" in nvidia.FIELDS


def test_policy_stub_dry_run_only():
    out = stub.suggest(None)
    assert out["gear_desired"] in hal_map.GEAR_ORDER
    assert out["source"] == "static-stub"


def test_blackbox_field_count():
    assert len(blog.REQUIRED_FIELDS) == 12


def test_acdc_dc_monotonic():
    pls = [acdc.DC_TABLE[k]["pl1_w"] for k in ("DC-1", "DC-2", "DC-3")]
    assert pls == sorted(pls, reverse=True)
