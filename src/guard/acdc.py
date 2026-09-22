"""AC-DC fallback (fence 4; P3 Step 3-4). Unknown -> DC (conservative)."""

DC_TABLE = {
    "DC-1": {"pl1_w": 35, "freq_ghz": 4.2, "min_soc": 60},
    "DC-2": {"pl1_w": 25, "freq_ghz": 3.8, "min_soc": 20},
    "DC-3": {"pl1_w": 15, "freq_ghz": 3.0, "min_soc": 0},
}
ACDC_FALLBACK_S = 1
AC_REARM_STABLE_S = 2
AC_FLAP_WINDOW_S = 300
AC_FLAP_LOCK_S = 1800


def select_dc_gear(soc_pct):
    try:
        soc = float(soc_pct)
    except (TypeError, ValueError):
        return "DC-3"
    if soc >= 60:
        return "DC-1"
    if soc >= 20:
        return "DC-2"
    return "DC-3"


def count_flips(history, now_s, window_s=AC_FLAP_WINDOW_S):
    evs = sorted([e for e in history if now_s - e[0] <= window_s], key=lambda x: x[0])
    flips = 0
    for i in range(1, len(evs)):
        if evs[i][1] != evs[i - 1][1]:
            flips += 1
    return flips


def on_power_event(event, history=None, now_s=0.0, ac_stable_s=0.0):
    """Power event handler (pure). UNKNOWN treated as DC."""
    history = list(history or [])
    et = (event or {}).get("type", "UNKNOWN")
    soc = (event or {}).get("soc_pct", 0)
    if et == "UNKNOWN":
        et = "AC_LOST"
    flips = count_flips(history, now_s)
    flap_lock = flips >= 3
    if flap_lock:
        return {"target_dc": "DC-2", "burst_terminate": True, "deadline_s": ACDC_FALLBACK_S,
                "ramp": [], "flap_lock": True, "flap_lock_s": AC_FLAP_LOCK_S,
                "deny": "AC_LOST", "reason": "flap>=3/5min lock DC-2 30min"}
    if et == "AC_LOST":
        gear = select_dc_gear(soc)
        return {"target_dc": gear, "burst_terminate": True, "deadline_s": ACDC_FALLBACK_S,
                "ramp": [], "flap_lock": False, "deny": "AC_LOST",
                "setpoints": {"pl1_w": DC_TABLE[gear]["pl1_w"],
                              "freq_ghz": DC_TABLE[gear]["freq_ghz"]}}
    if et == "AC_RESTORED":
        if float(ac_stable_s) < AC_REARM_STABLE_S:
            gear = select_dc_gear(soc)
            return {"target_dc": gear, "burst_terminate": True,
                    "deadline_s": ACDC_FALLBACK_S, "ramp": [], "flap_lock": False,
                    "deny": "AC_LOST", "reason": "wait-2s-stable"}
        cur = select_dc_gear(soc)
        order = ["DC-3", "DC-2", "DC-1"]
        idx = order.index(cur) if cur in order else 0
        ramp = order[idx:] + ["AC"]
        return {"target_dc": cur, "burst_terminate": False, "deadline_s": ACDC_FALLBACK_S,
                "ramp": ramp, "flap_lock": False, "deny": None}
    gear = select_dc_gear(soc)
    return {"target_dc": gear, "burst_terminate": True, "deadline_s": ACDC_FALLBACK_S,
            "ramp": [], "flap_lock": False, "deny": "AC_LOST"}
