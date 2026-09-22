# P4 Step 4-1 Collection Protocol (D_safe)

> Quota mirrors shadow gate 5.2: game >=2h / office >=2h / idle >=1h / >=1 plug event.
> Interactive probes >=15% (taskmgr cold/hot start, Alt-Tab, right-click).

## 1. Sample schema
Each row: (State48[48], Action7[7], perf/power/temp @+30s, versions, fluency_violation, gear, acdc, ts).

- State48: `src/state/state48.py` vector + valid mask (missing valid=0, no fill).
- Action7: [pl1_w, freq_ghz, uv_mv, epp, burst_allow, gear_idx, fan_req] (UV/burst/G4 locked pre-E5, mask=0).
- Targets @+30s: perf_score (0-100, higher better), power_w, temp_c.
- Versions: policy_ver/fence_ver/envelope_ver pinned per BlackBox 5.5.
- Fluency: 0/1 violation flag per fence Sec 2 (silent when no frames).

## 2. Coverage grid (W0-W7 x AC/DC nine-grid)
W0 idle / W1 office / W2 game / W3 compile / W4 video-call / W5 render / W6 browser / W7 plug-flap.
Each cell target >=80 rows for 2000-row D_safe (9 cells x ~220). AC/DC orthogonal, same priority.

## 3. Small-step live rule (pre-E5)
Delta PL<=5W / freq<=100MHz / UV step<=5mV. G4/burst/UV-deepening banned. Live needs E4/E5 + explicit confirm; default dry-run.

## 4. A/B split
A first (2000-4000 rows). B per P1-3 sampling ratio (M1/M3/M5/M7 mandatory, rest >=50%).
Datasets versioned append-only: `artifacts/datasets/D_safe_A_v1.csv` (+B). Real freeze = P6 replay buffer snapshot (read-only).

## 5. Current status
Real collection NOT started (needs 5h+ wall time). Synthetic D_safe_synth (2000 rows, physics-monotonic) validates pipeline only, tagged synthetic, never mixes with real.
Missing deps: lightgbm (owner P4 to add), onnx pkg (use onnxruntime CPU + torchscript fallback, M8 declaration).
