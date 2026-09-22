"""HAL_MAP tests (P3 Step 3-3)."""

import actuate.hal_map as h


def test_map_version_and_scale():
    assert h.HAL_MAP_VERSION == "1.0"
    assert h.UV_MV_TO_CODE_SCALE == 1.024
    assert len(h.GEAR_ORDER) == 4


def test_conversion_monotonic():
    codes = [h.uv_mv_to_code(mv) & 0xFFFF for mv in (0, -10, -50, -65)]

    def _s(u):
        return u - 0x10000 if u >= 0x8000 else u

    signed = [_s(c) for c in codes]
    assert signed[0] > signed[1] > signed[2] > signed[3]
    assert h.pl_w_to_reg(25) < h.pl_w_to_reg(40) < h.pl_w_to_reg(65)
    assert h.freq_ghz_to_ratio10(3.8) < h.freq_ghz_to_ratio10(4.8) < h.freq_ghz_to_ratio10(5.2)
    assert h.gear_to_setpoints("Quiet") == {"pl1_w": 25, "freq_ghz": 3.8}
    assert h.gear_to_setpoints("Balance")["pl1_w"] == 40
