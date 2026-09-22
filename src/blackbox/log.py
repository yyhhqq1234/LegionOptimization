"""BlackBox log (fence 5.5; P3 Step 3-2)."""

REQUIRED_FIELDS = (
    "policy_ver", "fence_ver", "envelope_ver", "state_hash", "action_raw",
    "shield_verdict", "setpoints_final", "temps", "power", "acdc",
    "burst_bucket", "fluency_stats",
)

_CAP = 20000
_RING = []


def clear():
    _RING.clear()


def __len__():
    return len(_RING)


def append(record):
    """Append one decision record. Missing fields -> ValueError."""
    if not isinstance(record, dict):
        raise ValueError("record must be dict")
    missing = [k for k in REQUIRED_FIELDS if k not in record]
    if missing:
        raise ValueError("missing fields: %s" % ",".join(missing))
    for k in ("policy_ver", "fence_ver", "envelope_ver"):
        v = record[k]
        if not isinstance(v, str) or not v:
            raise ValueError("bad version pin: %s" % k)
    _RING.append(dict(record))
    if len(_RING) > _CAP:
        del _RING[0:len(_RING) - _CAP]
    return len(_RING) - 1


def get(idx):
    return dict(_RING[idx])


def replay(policy_ver=None, fence_ver=None, envelope_ver=None):
    out = []
    for r in _RING:
        if policy_ver is not None and r.get("policy_ver") != policy_ver:
            continue
        if fence_ver is not None and r.get("fence_ver") != fence_ver:
            continue
        if envelope_ver is not None and r.get("envelope_ver") != envelope_ver:
            continue
        out.append(dict(r))
    return out


def completeness(records):
    total = len(records)
    if total == 0:
        return (0, 0)
    ok = 0
    for r in records:
        if all(k in r for k in REQUIRED_FIELDS):
            ok += 1
    return (ok, total)
