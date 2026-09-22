"""State48 builder (P3 Step 3-2).

Honest rules: missing -> valid=0, no fill; s46 const 0; s33记账 only.
"""

N_FEATURES = 48
S46_TS_INJECT_OK = 0

S33_BURST_TOKENS = 33
S44_VALID_SENSE = 44
S45_VALID_STATE = 45
S46_IDX = 46
S47_VALID_ACTION = 47

_RANGES = {
    "cpu_util": (0.0, 100.0),
    "cpu_temp_c": (20.0, 105.0),
    "gpu_util": (0.0, 100.0),
    "gpu_temp_c": (20.0, 95.0),
    "gpu_power_w": (0.0, 140.0),
    "pl1_w": (5.0, 120.0),
    "freq_ghz": (0.5, 6.0),
    "mem_pct": (0.0, 100.0),
    "burst_tokens_j": (0.0, 700.0),
    "soc_pct": (0.0, 100.0),
    "frame_p95_ms": (1.0, 100.0),
}


def _norm(key, val):
    lo, hi = _RANGES.get(key, (0.0, 1.0))
    if val is None:
        return 0.0
    try:
        f = float(val)
    except (TypeError, ValueError):
        return 0.0
    if f != f:
        return 0.0
    if hi <= lo:
        return 0.0
    r = (f - lo) / (hi - lo)
    if r < 0.0:
        return 0.0
    if r > 1.0:
        return 1.0
    return r


_SLOT_KEYS = [
    "cpu_util", "cpu_temp_c", "gpu_util", "gpu_temp_c",
    "gpu_power_w", "pl1_w", "freq_ghz", "mem_pct",
] + [None] * 25 + ["burst_tokens_j"] + [None] * 9 + [None, None, None, None, None]
while len(_SLOT_KEYS) < 48:
    _SLOT_KEYS.append(None)
_SLOT_KEYS = _SLOT_KEYS[:48]


def build_state48(raw):
    """Build State48 from raw telemetry. Missing -> 0.0/valid0, no fill."""
    if raw is None:
        raw = {}
    vec = [0.0] * N_FEATURES
    valid = [0] * N_FEATURES
    for i in range(N_FEATURES):
        if i == S46_IDX:
            vec[i] = 0.0
            valid[i] = 1
            continue
        if i in (S44_VALID_SENSE, S45_VALID_STATE, S47_VALID_ACTION):
            continue
        key = _SLOT_KEYS[i] if i < len(_SLOT_KEYS) else None
        if key is None:
            vec[i] = 0.0
            valid[i] = 0
            continue
        if key not in raw or raw[key] is None:
            vec[i] = 0.0
            valid[i] = 0
            continue
        v = raw[key]
        try:
            if isinstance(v, float) and v != v:
                vec[i] = 0.0
                valid[i] = 0
                continue
        except Exception:
            pass
        vec[i] = _norm(key, v)
        valid[i] = 1
    sense_seg = valid[0:8]
    state_seg = valid[8:33]
    act_seg = valid[34:44]

    def _mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    vec[S44_VALID_SENSE] = _mean(sense_seg)
    vec[S45_VALID_STATE] = _mean(state_seg)
    vec[S47_VALID_ACTION] = _mean(act_seg)
    valid[S44_VALID_SENSE] = 1 if any(sense_seg) else 0
    valid[S45_VALID_STATE] = 1 if any(state_seg) else 0
    valid[S47_VALID_ACTION] = 1 if any(act_seg) else 0
    return vec, valid
