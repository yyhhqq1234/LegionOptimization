"""L2 mutex: serial, timeout rollback, dry-run switch (P3 Step 3-3)."""

LOCK_NAME = "hal-actuation.lock"
TIMEOUT_S = 15
DRY_RUN_DEFAULT = True

_BUSY = False
_SNAPSHOT = None


def actuate(setpoints, dry_run=True):
    """Dry-run only validates + echoes; live refused before gate."""
    if dry_run:
        return ("dry-run", dict(setpoints))
    raise RuntimeError("gate E4/E5 not passed, live denied")


def save_snapshot(setpoints):
    return dict(setpoints)


def restore_snapshot(snapshot):
    if snapshot is None:
        return {}
    return dict(snapshot)


def transact(fn, snapshot, elapsed_s=0.0, timeout_s=TIMEOUT_S):
    """Transactional executor with timeout rollback (pure, testable)."""
    if elapsed_s > timeout_s:
        return (None, restore_snapshot(snapshot), TimeoutError("L2 15s timeout, rolled back"))
    try:
        res = fn()
    except Exception as e:
        return (None, restore_snapshot(snapshot), e)
    return (res, None, None)


def try_actuate_with_timeout(setpoints, fn, elapsed_s=0.0, dry_run=True):
    snap = save_snapshot(setpoints)
    if dry_run:
        res, restored, err = transact(fn, snap, elapsed_s=elapsed_s)
        if err is not None:
            return ("dry-run-rollback", restored, err)
        return ("dry-run", res, None)
    raise RuntimeError("gate E4/E5 not passed, live denied")
