"""Burst token bucket (fence 3; P3 Step 3-4)."""

BURST_TABLE = {
    "Quiet": {"p_sustained_w": 25, "p_burst_max_w": 40, "tmax_s": 10,
              "capacity_kj": 0.15, "refill_w": 3, "gap_s": 60},
    "Balance": {"p_sustained_w": 40, "p_burst_max_w": 65, "tmax_s": 28,
                "capacity_kj": 0.70, "refill_w": 5, "gap_s": 45},
    "Beast": {"p_sustained_w": 65, "p_burst_max_w": 95, "tmax_s": 20,
              "capacity_kj": 0.60, "refill_w": 8, "gap_s": 60},
    "Extreme": {"p_sustained_w": 65, "p_burst_max_w": 110, "tmax_s": 15,
                "capacity_kj": 0.675, "refill_w": 10, "gap_s": 90},
}
SAFETY_FACTOR = 1.2
EMPTY_FREEZE_N = 3
EMPTY_FREEZE_S = 300


def new_bucket(gear, tokens_j=None):
    row = BURST_TABLE[gear]
    cap_j = row["capacity_kj"] * 1000.0
    if tokens_j is None:
        tokens_j = cap_j
    return {
        "gear": gear, "tokens_j": float(tokens_j),
        "frozen_until_s": 0.0, "empty_strikes": 0, "last_burst_s": -1e9,
    }


def capacity_j(gear):
    return BURST_TABLE[gear]["capacity_kj"] * 1000.0


def update_bucket(bucket, power_w, dt_s, gear=None, temp_ok=True, now_s=0.0):
    """Token accounting (pure, returns new bucket)."""
    b = dict(bucket)
    g = gear or b.get("gear", "Balance")
    row = BURST_TABLE[g]
    cap = row["capacity_kj"] * 1000.0
    if now_s < float(b.get("frozen_until_s", 0.0)):
        b["gear"] = g
        return b
    tok = float(b.get("tokens_j", cap))
    p = float(power_w)
    dt = float(dt_s)
    if p > row["p_sustained_w"]:
        tok -= (p - row["p_sustained_w"]) * dt
        if tok < 0.0:
            tok = 0.0
    elif temp_ok:
        tok += row["refill_w"] * dt
        if tok > cap:
            tok = cap
    b["tokens_j"] = tok
    b["gear"] = g
    return b


def can_burst(bucket, est_energy_j, gear=None, temp_ok=True, now_s=0.0, last_gap_ok=True):
    b = bucket
    if now_s < float(b.get("frozen_until_s", 0.0)):
        return False
    if not temp_ok:
        return False
    if not last_gap_ok:
        return False
    return float(b.get("tokens_j", 0.0)) > float(est_energy_j) * SAFETY_FACTOR


def note_empty_request(bucket, now_s=0.0):
    b = dict(bucket)
    n = int(b.get("empty_strikes", 0)) + 1
    b["empty_strikes"] = n
    if n >= EMPTY_FREEZE_N:
        b["frozen_until_s"] = float(now_s) + EMPTY_FREEZE_S
        b["empty_strikes"] = 0
    return b


def note_success(bucket):
    b = dict(bucket)
    b["empty_strikes"] = 0
    return b


def check_tmax_violation(elapsed_s, gear):
    return float(elapsed_s) > float(BURST_TABLE[gear]["tmax_s"])
