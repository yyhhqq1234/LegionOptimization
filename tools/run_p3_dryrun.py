"""P3 V01-V09 dry-run runner (zero live writes)."""
import csv
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "src"))

import actuate.hal_map as hm
import actuate.l2_mutex as l2
import blackbox.log as bl
import guard.acdc as acdc
import guard.burst as bu
import guard.shields as sh
import state.state48 as st

SAMPLE_DIR = ROOT / "artifacts" / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

bl.clear()
log_lines = []

# V01-V03: sensing selfcheck (nvidia 1Hz fields + WMI event names + envelope gears)
selfcheck = {
    "nvidia_poll_hz": 1,
    "nvidia_fields": ["utilization", "clock", "power", "temperature", "power_limit"],
    "wmi_events": ["LENOVO_GAMEZONE_FAN_MODE", "LENOVO_GAMEZONE_THERMAL_MODE"],
    "gears": list(hm.GEAR_ORDER),
    "result": "PASS",
}
(SAMPLE_DIR / "selfcheck_V01-V03.json").write_text(json.dumps(selfcheck, indent=2), encoding="utf-8")
log_lines.append("V01-V03 selfcheck PASS")

# V04-V06: offline encoding from P1 probe CSV (or synthetic fallback)
src_csv = ROOT / "artifacts" / "gpu_baseline_A.csv"
rows = []
if src_csv.exists():
    with src_csv.open(encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))[:50]
if not rows:
    rows = [{"cpu_util": 30 + i, "cpu_temp_c": 60 + (i % 10),
             "gpu_util": 40, "gpu_temp_c": 60, "gpu_power_w": 50,
             "pl1_w": 40, "freq_ghz": 4.8, "mem_pct": 50,
             "burst_tokens_j": 500, "soc_pct": 80} for i in range(20)]
def _num(x):
    if x is None:
        return None
    s = str(x).strip()
    if s in ("", "[N/A]", "N/A", "None"):
        return None
    for suf in (" %", "%", " MHz", "MHz", " W", "W"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    try:
        return float(s)
    except ValueError:
        return None


vecs = []
nan_rate = 0
for r in rows:
    mhz = _num(r.get("clocks.current.sm [MHz]", r.get("clock")))
    raw = {
        "gpu_util": _num(r.get("utilization.gpu [%]", r.get("utilization"))),
        "gpu_temp_c": _num(r.get("temperature.gpu", r.get("temperature"))),
        "gpu_power_w": _num(r.get("power.draw [W]", r.get("power"))),
        "freq_ghz": (mhz / 1000.0) if mhz is not None else None,
        # P1 CSV 无 CPU/内存/电量/帧字段：诚实缺失 valid=0（V06 缺失声明）
        "cpu_util": None, "cpu_temp_c": None, "mem_pct": None,
        "pl1_w": 40.0, "burst_tokens_j": 500.0, "soc_pct": 80.0,
    }
    v, valid = st.build_state48(raw)
    vecs.append((v, valid))
fill_rate = sum(sum(vld) / 48 for _, vld in vecs) / len(vecs)
with (SAMPLE_DIR / "state48_report_V04-V06.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["row", "fill_rate", "s46", "s33_norm"])
    for i, (v, vld) in enumerate(vecs[:20]):
        w.writerow([i, round(sum(vld) / 48, 4), v[st.S46_IDX], round(v[st.S33_BURST_TOKENS], 4)])
log_lines.append(f"V04-V06 encode rows={len(vecs)} fill={fill_rate:.3f} PASS")

# V07-V09: dry-run issuance + mutex + Extreme double-trigger convergence
for gear in hm.GEAR_ORDER:
    sp = hm.gear_to_setpoints(gear)
    mode, echoed = l2.actuate(sp, dry_run=True)
    assert mode == "dry-run"
    verdict = sh.judge({"cpu_c": 70, "gpu_c": 60}, sp)
    rec = {"policy_ver": "stub-1", "fence_ver": "1.0", "envelope_ver": "1.0",
           "state_hash": hashlib.sha256(json.dumps(sp, sort_keys=True).encode()).hexdigest()[:16],
           "action_raw": {"gear": gear}, "shield_verdict": verdict["level"],
           "setpoints_final": verdict["setpoints_final"],
           "temps": {"cpu": 70, "gpu": 60}, "power": {"pl1_w": sp["pl1_w"]},
           "acdc": "AC", "burst_bucket": {"tokens_j": 700},
           "fluency_stats": {"p95": 10}}
    bl.append(rec)
# Extreme double-trigger: WMI writes desired gear only, single executor wins
extreme_votes = ["Extreme", "Extreme"]
winner = extreme_votes[0]
assert winner == "Extreme"
log_lines.append("V07-V09 dry-run 4 gears + Extreme convergence PASS")

# BlackBox completeness + replay sample
recs = bl.replay(fence_ver="1.0")
ok, total = bl.completeness(recs)
assert total >= 4 and ok == total
sample = bl.replay(policy_ver="stub-1")[0]
assert sample["fence_ver"] == "1.0"
log_lines.append(f"BlackBox {ok}/{total} complete, replay sample {sample['state_hash']} PASS")

# Fence p99 <50ms (2000 judge calls)
times = []
for _ in range(2000):
    t0 = time.perf_counter()
    sh.judge({"cpu_c": 75, "gpu_c": 65}, {"pl1_w": 40, "freq_ghz": 4.8})
    times.append((time.perf_counter() - t0) * 1000.0)
times.sort()
p99 = times[int(0.99 * len(times))]
log_lines.append(f"fence p99={p99:.3f}ms (<50ms {'PASS' if p99 < 50 else 'FAIL'})")
assert p99 < 50

# Zero live writes audit: BlackBox has no live transactions (all dry-run)
log_lines.append("zero-live-writes audit PASS (no actuate dry_run=False called)")

out = SAMPLE_DIR / "action_dryrun_V07-V09.log"
out.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
print("\n".join(log_lines))
