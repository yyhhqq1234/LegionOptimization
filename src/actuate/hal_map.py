"""L1 hal_map v1.0 (P3 Step 3-3)."""

HAL_MAP_VERSION = "1.0"
UV_MV_TO_CODE_SCALE = 1.024
GEAR_ORDER = ("Quiet", "Balance", "Beast", "Extreme")

GEAR_PL_W = {"Quiet": 25, "Balance": 40, "Beast": 65, "Extreme": 65}
GEAR_FREQ_GHZ = {"Quiet": 3.8, "Balance": 4.8, "Beast": 5.0, "Extreme": 5.2}


def uv_mv_to_code(mv):
    """UV mV -> FIVR code int (x1.024, 16bit unsigned of signed)."""
    code_signed = int(round(float(mv) * UV_MV_TO_CODE_SCALE))
    return code_signed & 0xFFFF


def uv_code_to_hex(mv):
    """UV mV -> 4-digit uppercase hex."""
    return "%04X" % uv_mv_to_code(mv)


def pl_w_to_reg(pl_w):
    """PL watts -> reg (PL*8, monotonic)."""
    return int(round(float(pl_w) * 8.0))


def freq_ghz_to_ratio10(freq_ghz):
    """Freq GHz -> ratio x10 (3.8 -> 38), monotonic."""
    return int(round(float(freq_ghz) * 10.0))


def gear_to_setpoints(gear):
    """Gear -> setpoints dict. Unknown gear -> ValueError."""
    if gear not in GEAR_ORDER:
        raise ValueError("unknown gear: %r" % (gear,))
    return {"pl1_w": GEAR_PL_W[gear], "freq_ghz": GEAR_FREQ_GHZ[gear]}
