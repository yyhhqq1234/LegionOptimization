"""Replay test (P3 Step 3-4 gate: L2+ false pass = 0)."""

import csv
from pathlib import Path

import guard.shields as s

ROOT = Path(__file__).resolve().parent.parent


def _rows(name, limit=20):
    p = ROOT / "artifacts" / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8", errors="ignore") as f:
        r = csv.DictReader(f)
        return [row for _, row in zip(range(limit), r)]


def test_replay_no_l2_false_pass():
    gpu_rows = _rows("gpu_baseline_A.csv")
    assert gpu_rows, "P1 gpu_baseline_A.csv missing, replay not run"
    false_pass = 0
    checked = 0
    for row in gpu_rows:
        try:
            cpu = float(row.get("cpu_temp_c", row.get("temperature", 60)) or 60)
            gpu = float(row.get("gpu_temp_c", row.get("temperature", 55)) or 55)
        except ValueError:
            continue
        v = s.judge({"cpu_c": cpu, "gpu_c": gpu}, {"pl1_w": 40, "freq_ghz": 4.8})
        checked += 1
        overall, _, _ = s.temp_level(cpu, gpu)
        if overall in ("L2", "L3") and v["level"] not in ("L2", "L3"):
            false_pass += 1
    assert checked > 0
    assert false_pass == 0
