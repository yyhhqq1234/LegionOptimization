"""Synthetic D_safe B (heterogeneous shift, pipeline only, tagged synthetic)."""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "samples" / "D_safe_synth_B_v1.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

random.seed(7)
GEARS = ["Quiet", "Balance", "Beast", "Extreme"]
WORKS = ["W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7"]

# B sampling ratio: M1/M3/M5/M7 mandatory, rest >=50% -> 1200 rows total
N = 1200
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["synthetic", "machine", "work", "acdc", "gear", "pl1_w", "freq_ghz",
                "cpu_util", "gpu_util", "perf_score", "power_w", "temp_c",
                "fluency_violation", "policy_ver", "fence_ver", "envelope_ver"])
    for i in range(N):
        work = WORKS[i % 8]
        acdc = "DC" if ((i // 8) % 2) == 1 else "AC"
        gear = GEARS[(i // 24) % 4]
        pl1 = {"Quiet": 25, "Balance": 40, "Beast": 65, "Extreme": 65}[gear]
        freq = {"Quiet": 3.8, "Balance": 4.8, "Beast": 5.0, "Extreme": 5.2}[gear]
        # heterogeneous shift: B runs hotter (+4C) and 5% hungrier power
        cpu = random.uniform(5, 95)
        gpu = random.uniform(5, 95)
        perf = min(100, freq * 11.5 + cpu * 0.28 + random.gauss(0, 3))
        power = pl1 * 0.7 * 1.05 + cpu * 0.26 + random.gauss(0, 2)
        temp = 49 + power * 0.35 + random.gauss(0, 1.5)
        fl = 1 if (work in ("W2", "W4") and random.random() < 0.09) else 0
        w.writerow([1, "B", work, acdc, gear, pl1, freq, round(cpu, 1), round(gpu, 1),
                    round(perf, 1), round(power, 1), round(temp, 1), fl,
                    "stub-1", "1.0", "1.0"])
print(f"wrote {OUT} {N} rows")
