"""L3 shields + arbitration (P3 Step 3-4).

Thresholds from fence v1.0; runtime temps are relative to TJMax, no hardcode.
"""

FENCE_VERSION = "1.0"
ARBITRATION_PRIORITY = ("temperature", "acdc", "power_cap", "fluency", "burst")

TEMP_WARN_CPU = 90
TEMP_L1_CPU = 95
TEMP_L2_CPU = 98
TEMP_L3_CPU = 100
TEMP_WARN_GPU = 80
TEMP_L1_GPU = 85
TEMP_L2_GPU = 88
TEMP_L3_GPU = 90
DC_TEMP_OFFSET = -2

DEBOUNCE_N = 3
TEMP_HOLD_S = 30
FLUENCY_HOLD_S = 10

DENY_CODES = ("TEMP", "SMOOTH", "BURST_EMPTY", "AC_LOST", "MANUAL_PIN")

REARM_CPU_C = 80
REARM_GPU_C = 70
REARM_L2_S = 30
REARM_L3_S = 60


def temp_level(cpu_c, gpu_c, dc_mode=False):
    """Return (overall, cpu_level, gpu_level). Overall is max of CPU/GPU."""
    off = DC_TEMP_OFFSET if dc_mode else 0

    def _lvl_cpu(t):
        if t >= TEMP_L3_CPU + off:
            return "L3"
        if t >= TEMP_L2_CPU + off:
            return "L2"
        if t >= TEMP_L1_CPU + off:
            return "L1"
        if t >= TEMP_WARN_CPU + off:
            return "WARN"
        return "OK"

    def _lvl_gpu(t):
        if t >= TEMP_L3_GPU + off:
            return "L3"
        if t >= TEMP_L2_GPU + off:
            return "L2"
        if t >= TEMP_L1_GPU + off:
            return "L1"
        if t >= TEMP_WARN_GPU + off:
            return "WARN"
        return "OK"

    order = {"OK": 0, "WARN": 1, "L1": 2, "L2": 3, "L3": 4}
    cl, gl = _lvl_cpu(float(cpu_c)), _lvl_gpu(float(gpu_c))
    overall = cl if order[cl] >= order[gl] else gl
    return overall, cl, gl


def l1_clip_action(setpoints):
    """L1 soft clip: PL1 down one gear + freq -200MHz + burst zero."""
    out = dict(setpoints)
    try:
        out["pl1_w"] = float(out.get("pl1_w", 40)) - 15.0
        if out["pl1_w"] < 15.0:
            out["pl1_w"] = 15.0
    except Exception:
        out["pl1_w"] = 25.0
    try:
        out["freq_ghz"] = float(out.get("freq_ghz", 4.8)) - 0.2
    except Exception:
        out["freq_ghz"] = 3.8
    out["burst_allowed"] = 0
    out["deny"] = "TEMP"
    return out


def l2_trip_action():
    """L2 trip: force Quiet floor + pause policy + lock burst."""
    return {
        "pl1_w": 25, "freq_ghz": 3.8, "burst_allowed": 0,
        "policy_paused": True, "deny": "TEMP", "level": "L2",
    }


def l3_fallback_action():
    """L3 critical: immediate L3 fallback (static Quiet + bypass)."""
    return {
        "pl1_w": 25, "freq_ghz": 3.8, "burst_allowed": 0,
        "policy_bypassed": True, "deny": "TEMP", "level": "L3",
        "fallback": "quiet.bat-equivalent",
    }


def rearm_ok(cpu_c, gpu_c, hold_s, need_s=REARM_L2_S):
    """Rearm: CPU<80 and GPU<70 for need_s (default L2 30s)."""
    if float(cpu_c) < REARM_CPU_C and float(gpu_c) < REARM_GPU_C:
        return float(hold_s) >= float(need_s)
    return False


def stale_conservative(stale=True):
    """Stale/wild samples -> most conservative: temp as overheat (L2)."""
    if stale:
        return {"level": "L2", "deny": "TEMP", "conservative": True,
                "action": l2_trip_action()}
    return {"level": "OK", "deny": None, "conservative": False}


def debounce_trigger(hits, n=DEBOUNCE_N):
    """Debounce: N consecutive hits to confirm."""
    return int(hits) >= int(n)


FLUENCY_P95_RATIO = 1.15
FLUENCY_LOW_RATIO = 0.80
FLUENCY_JANK_N = 12
FLUENCY_JANK_SEQ = 6
FLUENCY_DWM_DROP = 0.05
FLUENCY_SUPPRESS_S = 5.0


def fluency_trigger(p95_ms, baseline_p95_ms, low_fps=None, baseline_low_fps=None,
                    jank_n=0, jank_seq=0, dwm_drop=0.0, app_class="game-fullscreen",
                    has_frames=True, since_switch_s=1e9):
    """Fluency trigger (caller debounces 2 windows). Returns (hit, reason)."""
    if not has_frames:
        return False, "silent-no-frames"
    if app_class in ("idle-desktop", "idle"):
        return False, "silent-idle"
    if float(since_switch_s) < FLUENCY_SUPPRESS_S:
        if int(jank_n) >= FLUENCY_JANK_N * 2 or int(jank_seq) >= FLUENCY_JANK_SEQ * 2:
            return True, "jank-burst-suppressed-window"
        return False, "suppressed-switch"
    if baseline_p95_ms and float(p95_ms) > float(baseline_p95_ms) * FLUENCY_P95_RATIO:
        return True, "p95-degraded"
    if (low_fps is not None and baseline_low_fps
            and float(low_fps) < float(baseline_low_fps) * FLUENCY_LOW_RATIO):
        return True, "low-drop"
    if int(jank_n) >= FLUENCY_JANK_N or int(jank_seq) >= FLUENCY_JANK_SEQ:
        return True, "jank-cluster"
    if float(dwm_drop) > FLUENCY_DWM_DROP:
        return True, "dwm-degraded"
    return False, "ok"


def fluency_hold_action(current_gear, gear_order=("Quiet", "Balance", "Beast", "Extreme")):
    """Hold: deny downshifts (freeze), at most one step up if temp allows."""
    idx = gear_order.index(current_gear) if current_gear in gear_order else 1
    up = gear_order[idx + 1] if idx + 1 < len(gear_order) else None
    return {"gear_hold": current_gear, "gear_up": up, "hold_s": FLUENCY_HOLD_S,
            "deny": "SMOOTH", "single_step": True}


def arbitrate(trigger_sources):
    """Most-conservative union + full source log."""
    if not trigger_sources:
        return {"winner": None, "level_rank": 0, "all_sources": []}
    ordered = sorted(trigger_sources, key=lambda x: x[1], reverse=True)
    return {"winner": ordered[0][0], "level_rank": ordered[0][1],
            "all_sources": [t[0] for t in trigger_sources],
            "details": [t[2] if len(t) > 2 else None for t in trigger_sources]}


def judge(state48, action_raw):
    """Fence verdict (sync pure fn, p99 well under 50ms)."""
    import time
    t0 = time.perf_counter()
    if isinstance(state48, dict):
        cpu = state48.get("cpu_c", 60)
        gpu = state48.get("gpu_c", 55)
        dc = bool(state48.get("dc_mode", False))
        stale = bool(state48.get("stale", False))
    else:
        try:
            cpu = 20.0 + float(state48[1]) * 85.0
            gpu = 20.0 + float(state48[3]) * 75.0
        except Exception:
            cpu, gpu = 60.0, 55.0
        dc, stale = False, False
    if stale:
        v = stale_conservative(True)
        v["trigger_sources"] = ["temperature(stale)"]
        v["setpoints_final"] = v["action"]
        v["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
        return v
    overall, _, _ = temp_level(cpu, gpu, dc_mode=dc)
    triggers = []
    if overall in ("WARN", "L1", "L2", "L3"):
        rank = {"WARN": 1, "L1": 2, "L2": 3, "L3": 4}[overall]
        triggers.append(("temperature", rank, overall))
    arb = arbitrate(triggers)
    base = dict(action_raw) if isinstance(action_raw, dict) else {"gear": "Balance"}
    if overall == "L1":
        final = l1_clip_action({"pl1_w": base.get("pl1_w", 40),
                                "freq_ghz": base.get("freq_ghz", 4.8)})
    elif overall == "L2":
        final = l2_trip_action()
    elif overall == "L3":
        final = l3_fallback_action()
    else:
        final = dict(base)
        final["deny"] = None
    out = {"level": overall, "deny": final.get("deny"),
           "setpoints_final": final,
           "trigger_sources": arb["all_sources"],
           "winner": arb["winner"]}
    out["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
    return out
