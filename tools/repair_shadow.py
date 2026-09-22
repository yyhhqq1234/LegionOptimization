"""Repair shadow CSV: keep rows matching header width, archive part1."""
import csv
import os

SRC = "artifacts/datasets/D_safe_shadow_A.csv"
DST = "artifacts/datasets/D_safe_shadow_A_part1.csv"

with open(SRC, encoding="utf-8") as f:
    rows = list(csv.reader(f))
hdr = rows[0]
good = [r for r in rows[1:] if len(r) == len(hdr)]
bad = len(rows) - 1 - len(good)
with open(DST, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(good)
os.remove(SRC)
print(f"kept={len(good)} dropped_misaligned={bad} -> part1")
