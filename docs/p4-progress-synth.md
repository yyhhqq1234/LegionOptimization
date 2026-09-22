# P4 Progress (synthetic pipeline, real collection pending)

> Goal: D_safe>=2000/machine 9-grid>=80% + 3-model compare + replay Return+10% shield-flat + ONNXv1 <10MB <5ms.
> Status: PIPELINE GREEN on synthetic; REAL data collection NOT started (needs 5h+ wall: game2h/office2h/idle1h+plug).

## 1. Done (synthetic, tagged)
- Protocol: `docs/p4-collection-protocol.md` (15% interactive, 9-grid quota, small-step live rule).
- D_safe_synth_A_v1: 2000 rows, physics-monotonic, `artifacts/samples/D_safe_synth_A_v1.csv`.
- Surrogate: `src/policy/surrogate.py` MLP 64-64-32+LN + Ensemble5, loss MSE+0.2Rank+monotonic, AdamW 3e-4/b256/early20.
- Train: `tools/train_p4_synth.py` cuda, MLP val_mse 0.0814, test RMSE 3.22/2.89/1.73, MAE 2.56/2.18/1.39, tau 0.816.
- Export: torchscript-fallback 0.05MB latency 0.16ms (PASS <10MB <5ms). ONNX pkg missing -> M8 declaration, not blocked.
- LightGBM: MISSING (owner P4 to pip install before baseline; MLP/Ensemble used).

## 2. V10-V15 (synthetic replay)
- V10-V12 reward replay: computable 100% on synthetic; B2 anchor distribution awaits real B2 logs.
- V13-V15 envelope: 4-gear dry-run violation=0 (P3 shields); floor/SLO await t4 thresholds + real small-step (G4 excluded).
- Return = mean-0.5std-2shield-1clamp +10% vs B2: PENDING real anchor (synthetic has no B2 baseline).

## 4. Real shadow (round4-5, read-only, job running)
- Collector `tools/collect_shadow.py` 1Hz (nvidia-smi + scheme query, zero writes), 5h bg job pwsh-1.
- Smoke 15 rows + bg growth: 95 (r4) -> 120 (r5) -> 167 (r6, W0/AC) -> 555 real (r12: part1 508 + part2 47, W0/AC), mean State48 fill 0.167 (GPU4 + pl1/burst/soc + s46; CPU/mem honest missing, fps/p95 empty). pytest 45 green.
- Commit 9dab39f pushed (502 x2 then OK). Data `artifacts/datasets/` gitignored per iron law 10.
- Still needs: W1/W2/game/office/idle rotation + 1 plug event for 8h E4 coverage; live E4/E5 gate.
- LightGBM + onnx/onnxscript: installed round1 (4.7.0/1.23.0), requirements locked.

Next: keep shadow running (overnight) or proceed P5 transfer design on synthetic.
