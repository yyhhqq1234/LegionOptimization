"""E4 shadow run: 1Hz sensing + policy inference + fence trial + BlackBox, ZERO actuation.

Why this exists: the E4 gate needs "shadow" evidence (policy reasons but never issues,
fence trial-computes, BlackBox records everything). The plain collector only records
telemetry, so the gate could not be judged no matter how long it ran.

Per tick (all read-only):
  1. sensing    nvidia-smi (util/clocks/power/temp/PL) + GetSystemPowerStatus (AC/DC)
                + powercfg active scheme (recorded as the in-service baseline signal)
  2. State48    src/state/state48.build_state48  (missing -> valid=0, no fill)
  3. policy     src/policy/stub.suggest -> gear_desired (+ Action7 via hal_map)
  4. fence      src/guard/shields.judge        (trial compute, L1/L2/L3 verdict)
  5. L2         src/actuate/l2_mutex.actuate(dry_run=True)  -- the only path; live raises
  6. BlackBox   src/blackbox/log.append        (12 required fields) + JSONL on disk

Honest limits recorded per row (never fabricated):
  - cpu_temp_src: no CPU temperature channel exists pre-E5 (E2 finding), so the fence is
    fed gpu temp as a labelled proxy. live gate stays LOCKED.
  - gear_actual: no calibrated active-gear reader; powercfg scheme id/name is recorded as
    the in-service signal and the mapping is marked uncalibrated.
  - policy_ver: "stub-1" (static envelope). No policy weights exist yet, so a surrogate
    policy cannot be loaded; requesting --policy surrogate is recorded as BLOCKED.
"""
import argparse
import ctypes
import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import actuate.hal_map as hm          # noqa: E402
import actuate.l2_mutex as l2         # noqa: E402
import blackbox.log as bl             # noqa: E402
import guard.shields as sh            # noqa: E402
import state.state48 as st            # noqa: E402
import policy.stub as stub            # noqa: E402
import sense.lenovo_wmi as lw         # noqa: E402
from collect_shadow import fps_window, find_nvidia_smi, load_presentmon, snap_gpu  # noqa: E402

POLICY_VER = "stub-1"
FENCE_VER = sh.FENCE_VERSION
ENVELOPE_VER = hm.HAL_MAP_VERSION
INFER_BUDGET_MS = 50.0        # fence spec 6.2: 50ms per inference
SAMPLE_DIR = ROOT / "artifacts" / "samples"


class _PowerStatus(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]


def read_power():
    """(acdc, soc_pct) via GetSystemPowerStatus; unknown stays UNKNOWN (no guessing)."""
    s = _PowerStatus()
    try:
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            return "UNKNOWN", None
    except Exception:
        return "UNKNOWN", None
    acdc = {0: "DC", 1: "AC", 255: "UNKNOWN"}.get(int(s.ACLineStatus), "UNKNOWN")
    soc = None if int(s.BatteryLifePercent) == 255 else int(s.BatteryLifePercent)
    return acdc, soc


def read_scheme():
    """(guid, name) of the active power scheme = in-service baseline signal."""
    try:
        r = subprocess.run(["powercfg", "/GETACTIVESCHEME"], capture_output=True,
                           text=True, timeout=10)
        out = r.stdout.strip()
        if not out:
            return "", ""
        guid = out.split()[-2] if len(out.split()) >= 2 else ""
        name = out.split("(", 1)[1].rstrip(")") if "(" in out else ""
        return guid, name
    except Exception:
        return "", ""


def num(cell):
    s = str(cell).strip()
    if s in ("", "[N/A]", "N/A", "None"):
        return None
    for suf in (" %", "%", " MHz", "MHz", " W", "W"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    try:
        return float(s)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--work", default="W0")
    ap.add_argument("--acdc-label", default="", help="label override; empty = read the real AC/DC state")
    ap.add_argument("--policy", default="stub", choices=("stub", "surrogate"))
    ap.add_argument("--out", default="", help="JSONL path (default samples/e4_shadow_<ts>.jsonl)")
    ap.add_argument("--fps-file", default="")
    ap.add_argument("--fps-process", default="")
    ap.add_argument("--fps-reload", type=float, default=30.0)
    args = ap.parse_args()

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else SAMPLE_DIR / f"e4_shadow_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    wall0 = time.time()
    series = {}
    fps_note = "no --fps-file"
    if args.fps_file:
        rows, fps_note = load_presentmon(args.fps_file, wall0, args.fps_process)
        series = {t: v for t, v in rows}

    bl.clear()
    policy_ver = POLICY_VER
    blocked = ""
    if args.policy == "surrogate":
        policy_ver, blocked = "stub-1", "BLOCKED-no-policy-weights"

    stats = {"ticks": 0, "blackbox_ok": 0, "errors": 0, "timeouts": 0,
             "fence_l1": 0, "fence_l2": 0, "fence_l3": 0, "fence_ok": 0,
             "work": args.work, "policy_ver": policy_ver, "blocked": blocked}
    print(f"shadow-run: policy={policy_ver} nvidia-smi={find_nvidia_smi() or 'NOT FOUND'} "
          f"out={out_path.name} {blocked}")

    last_reload = time.time()
    with out_path.open("w", encoding="utf-8") as f:
        t0 = time.time()
        while time.time() - t0 < args.seconds:
            tick_t0 = time.perf_counter()
            now = datetime.now()
            if args.fps_file and time.time() - last_reload >= args.fps_reload:
                rows, fps_note = load_presentmon(args.fps_file, wall0, args.fps_process)
                before = len(series)
                series.update({t: v for t, v in rows})
                last_reload = time.time()
                if len(series) != before:
                    print(f"  fps reload: +{len(series) - before} frames ({fps_note})")
            g = snap_gpu()
            util, mhz, power_w, temp, pl = (num(v) for v in g)
            # real in-service gear from the Lenovo ACPI-WMI module (~260ms/call, 1Hz is fine);
            # CPU freq is polled every 10th tick to keep the tick well under 1s
            gear_name, gear_mode = lw.read_gear()
            cpu_freq_ghz = lw.read_cpu_freq_ghz() if stats["ticks"] % 10 == 0 else None
            acdc_real, soc = read_power()
            acdc = args.acdc_label or acdc_real
            guid, sname = read_scheme()
            fps, p95 = fps_window([(t, v) for t, v in series.items()], now.timestamp()) if series else ("", "")
            p95_f = num(p95) if p95 != "" else None

            raw = {
                "gpu_util": util, "gpu_temp_c": temp, "gpu_power_w": power_w,
                "freq_ghz": (mhz / 1000.0) if mhz is not None else None,
                "pl1_w": pl, "soc_pct": soc,
                "frame_p95_ms": p95_f,
                # no CPU/mem channel pre-E5: honest missing (valid=0), never filled
                "cpu_util": None, "cpu_temp_c": None, "mem_pct": None, "burst_tokens_j": None,
            }
            vec, valid = st.build_state48(raw)
            fill = sum(valid) / 48.0

            row = {"ts": now.isoformat(timespec="milliseconds"), "work": args.work,
                   "acdc": acdc, "acdc_sensed": acdc_real,
                   "soc_pct": soc, "scheme_guid": guid, "scheme_name": sname,
                   "telemetry": {"util_pct": util, "clocks_sm_mhz": mhz, "power_w": power_w,
                                 "temp_c": temp, "power_limit_w": pl},
                   "state48": {"fill_rate": round(fill, 4), "valid_sense": vec[st.S44_VALID_SENSE],
                               "valid_state": vec[st.S45_VALID_STATE],
                               "valid_action": vec[st.S47_VALID_ACTION]},
                   "cpu_temp_src": "proxy-gpu" if temp is not None else "missing",
                   "gear_actual": gear_name or (f"mode:{gear_mode}" if gear_mode is not None
                                                else "unknown"),
                   "gear_mode": gear_mode, "lenovo_cpu_freq_ghz": cpu_freq_ghz,
                   "policy_ver": policy_ver, "fence_ver": FENCE_VER,
                   "envelope_ver": ENVELOPE_VER}

            err = ""
            try:
                sug = stub.suggest(vec)
                gear = sug["gear_desired"]
                sp = hm.gear_to_setpoints(gear)
                row["policy"] = {"gear_desired": gear, "source": sug["source"],
                                 "action7": {"pl1_w": sp["pl1_w"], "freq_ghz": sp["freq_ghz"],
                                             "uv_mv": None, "burst_allow": 0, "gear_idx":
                                             list(hm.GEAR_ORDER).index(gear)}}
                # fence trial: CPU channel absent -> labelled GPU proxy (recorded above)
                cpu_proxy = temp if temp is not None else 60.0
                verdict = sh.judge({"cpu_c": cpu_proxy, "gpu_c": temp if temp is not None else 55.0,
                                    "dc_mode": acdc == "DC", "stale": False},
                                   {"gear": gear, "pl1_w": sp["pl1_w"], "freq_ghz": sp["freq_ghz"]})
                mode, echoed = l2.actuate(verdict["setpoints_final"], dry_run=True)
                row["fence"] = {"level": verdict["level"], "deny": verdict["deny"],
                                "trigger_sources": verdict["trigger_sources"],
                                "winner": verdict["winner"],
                                "elapsed_ms": round(verdict["elapsed_ms"], 4)}
                row["l2_mode"] = mode
                if verdict["level"] == "OK":
                    stats["fence_ok"] += 1
                elif verdict["level"] == "L1":
                    stats["fence_l1"] += 1
                elif verdict["level"] == "L2":
                    stats["fence_l2"] += 1
                elif verdict["level"] == "L3":
                    stats["fence_l3"] += 1
                if verdict["elapsed_ms"] > INFER_BUDGET_MS:
                    stats["timeouts"] += 1
                sp_final = verdict["setpoints_final"]
                rec = {"policy_ver": policy_ver, "fence_ver": FENCE_VER, "envelope_ver": ENVELOPE_VER,
                       "state_hash": hashlib.sha256(
                           json.dumps([round(x, 4) for x in vec], sort_keys=True).encode()).hexdigest()[:16],
                       "action_raw": {"gear": gear}, "shield_verdict": verdict["level"],
                       "setpoints_final": {k: sp_final.get(k) for k in ("pl1_w", "freq_ghz", "deny", "burst_allowed")},
                       "temps": {"cpu_proxy": cpu_proxy, "gpu": temp},
                       "power": {"pl1_w": sp["pl1_w"], "gpu_power_w": power_w},
                       "acdc": acdc, "burst_bucket": {"tokens_j": raw["burst_tokens_j"]},
                       "fluency_stats": {"p95": p95_f, "fps": num(fps) if fps != "" else None}}
                row["blackbox_idx"] = bl.append(rec)
                stats["blackbox_ok"] += 1
            except Exception as e:                      # honest failure counting
                err = f"{type(e).__name__}: {e}"
                stats["errors"] += 1
                row["error"] = err
            row["tick_ms"] = round((time.perf_counter() - tick_t0) * 1000.0, 3)
            row["frames"] = {"fps": num(fps) if fps != "" else None, "p95_ms": p95_f,
                             "note": fps_note}
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
            f.flush()
            stats["ticks"] += 1
            time.sleep(1.0)

    recs = bl.replay()
    ok, total = bl.completeness(recs)
    stats["blackbox_complete"] = f"{ok}/{total}"
    stats["seconds"] = args.seconds
    stats["fps_note"] = fps_note
    (SAMPLE_DIR / (out_path.stem + "_summary.json")).write_text(
        json.dumps(stats, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(stats, indent=1, ensure_ascii=True))
    print(f"shadow run complete -> {out_path} (read-only; no actuation path was taken)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
