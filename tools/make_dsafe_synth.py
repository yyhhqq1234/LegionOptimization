"""Synthetic D_safe generator (pipeline validation only, tagged synthetic)."""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

random.seed(42)
GEARS = ["Quiet", "Balance", "Beast", "Extreme"]
WORKS = ["W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7"]

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    hdr = ["synthetic", "work", "acdc", "gear", "pl1_w", "freq_ghz", "cpu_util",
           "gpu_util", "perf_score", "power_w", "temp_c", "fluency_violation",
           "policy_ver", "fence_ver", "envelope_ver"]
    w.writerow(hdr)
    for i in range(2000):
        work = WORKS[i % 8]
        acdc = "DC" if (i // 8) % 4 == 3 else "AC"
        gear = GEARS[(i // 32) % 4]
        pl1 = {"Quiet": 25, "Balance": 40, "Beast": 65, "Extreme": 65}[gear]
        freq = {"Quiet": 3.8, "Balance": 4.8, "Beast": 5.0, "Extreme": 5.2}[gear]
        cpu = random.uniform(5, 95)
        gpu = random.uniform(5, 95)
        # physics-monotonic: perf up with freq/util, power up with pl1/util, temp up with power
        perf = min(100, freq * 12 + cpu * 0.3 + random.gauss(0, 3))
        power = pl1 * 0.7 + cpu * 0.25 + random.gauss(0, 2)
        temp = 45 + power * 0.35 + random.gauss(0, 1.5)
        fl = 1 if (work in ("W2", "W4") and random.random() < 0.08) else 0
        w.writerow([1, work, acdc, gear, pl1, freq, round(cpu, 1), round(gpu, 1),
                    round(perf, 1), round(power, 1), round(temp, 1), fl,
                    "stub-1", "1.0", "1.0"])
print(f"wrote {OUT} 2000 rows")
