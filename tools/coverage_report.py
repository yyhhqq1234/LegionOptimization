"""Coverage monitor: 8 works x AC/DC grid fill + interactive ratio (read-only)."""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "artifacts" / "datasets"
WORKS = ["W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7"]
CELL_TARGET = 80

rows = []
for p in sorted(DATA.glob("D_safe_shadow_A*.csv")):
    try:
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("work") and r.get("acdc"):
                    rows.append(r)
    except OSError:
        continue
c = Counter((r["work"], r["acdc"]) for r in rows)
cells = {(w, a): c.get((w, a), 0) for w in WORKS for a in ("AC", "DC")}
covered = sum(1 for v in cells.values() if v >= CELL_TARGET)
inter = sum(1 for r in rows if r.get("work") in ("W1", "W6"))
out = {"rows": len(rows), "cells": {f"{k[0]}/{k[1]}": v for k, v in sorted(cells.items())},
       "covered_ge80": covered, "coverage": round(covered / 16, 3),
       "interactive_ratio": round(inter / len(rows), 3) if rows else 0.0,
       "target_per_cell": CELL_TARGET, "synthetic": False}
print(json.dumps(out, indent=1))
missing = [k for k, v in sorted(cells.items()) if v < CELL_TARGET]
if missing:
    print("MISSING quilt:", ", ".join(f"{w}/{a}({v})" for (w, a), v in
          [((w, a), cells[(w, a)]) for w in WORKS for a in ("AC", "DC")] if v < CELL_TARGET),
          file=sys.stderr)
