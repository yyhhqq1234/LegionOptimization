# P4 Evidence Index (acceptance -> evidence)

> Objective: D_safe>=2000/machine 9-grid>=80% + 3-model + replay Return+10% shield-flat + ONNXv1 <10MB <5ms + tag phase-04-done.
> Legend: DONE-syn = synthetic pipeline proof; OPEN = needs operator/wall-time/live.
> r27 (2026-10-14): shadow counts now exclude the r26 rollup (was double counted).

## 1. D_safe scale (OPEN, collecting — stopped 2026-09-22 22:08)
- Synth A 2000 16/16 (`samples/D_safe_synth_A_v1.csv`, `tools/make_dsafe_synth.py`).
- Synth B 1200 hetero (`samples/D_safe_synth_B_v1.csv`, `tools/make_dsafe_synth_B.py`).
- Real: **48753 rows / 13.54h** = W0/AC 34944 (9.71h) + W1/AC 6902 (1.92h) + W2/AC 6907 (1.92h);
  coverage **3/16**, interactive_ratio **0.142** (`tools/collect_shadow.py`, `tools/coverage_report.py`).
  r27: the r26 rollup table (`D_safe_shadow_A.csv`, 34481 rows) double counted 10352 keys and
  inflated the report to 83234; archived to `datasets/archive/`, counts are part-only now.
- Missing: W3-W7 x AC/DC rotation, real plug event (`tools/plug_watch.py` ready), and the
  E4 shadow-run link (see §6) — perf labels chain is ready (§5).

## 2. Three-model compare (DONE-syn; real rerun honest-partial)
- MLP val 0.08, RMSE 3.23/2.94/1.74, tau 0.815; LGB 2.88/2.11/1.70 (honest: LGB wins on synth); ENS undertrained.
- Report `samples/p4_full_compare.json` + `samples/p4_synth_compare.json`; code `tools/train_p4_full.py`, `src/policy/surrogate.py`.
- Cross-machine A->B RMSE 3.33/2.66/1.74 vs same-A 3.10/2.69/1.66 (`samples/cross_AB.json`, `tools/cross_AB_synth.py`).
- Real pilot: 600 rows power 0.19 beats mean 0.26; then n1147 narrow-idle loses; then
  **n12081 (all real parts) RMSE power 0.776 / temp 0.826 vs mean 6.463 / 3.493** —
  beats mean by 88% on power, worse than the narrow-idle 0.236 (wide distribution, honest).
  perf head still `BLOCKED-no-frame-labels` at that run (`samples/real_pilot.json`, `tools/pilot_real_train.py`).

## 3. Replay Return+10% shield-flat (OPEN)
- Synth raw -7.6%, BO-constrained +1.3% shield-flat (`samples/bo_synth_result.json`, `tools/bo_p4_synth.py`).
- V12 B2 anchor proxy mean 71.4 p50 74.9 (B0/B1/B2 logs missing, frozen-config x surrogate, `samples/reward_baseline_B2.csv`, `tools/reward_baseline_B2.py`).
- B2 four-gear dry-run 4/4 OK violation 0 (`samples/envelope_B2_dryrun.json`).
- Blocked: real multi-grid + perf labels + small-step live (E4/E5 gate; user small-step confirm logged, gate missing -> live LOCKED).

## 4. ONNX v1 (DONE-syn)
- `samples/predictor_v1.onnx` (+`.data`) 0.02MB, CPU 0.02ms (PASS <10MB <5ms). Deps locked: lightgbm 4.7.0, onnx 1.23.0, onnxscript (`requirements.txt`).

## 5. Protocols/tools (DONE)
- `docs/p4-collection-protocol.md` (15% interactive, 9-grid quota, small-step rule).
- `tools/interactive_probe.py` (cold 608ms / hot 88ms verified), `tools/plug_watch.py` (status2/95pct, no real plug event yet).
- Shadow pilot `samples/shadow_pilot.json`, `samples/selfcheck_V01-V03.json`, `samples/state48_report_V04-V06.csv`, `samples/action_dryrun_V07-V09.log`.
- **r27 perf label chain**: `tools/presentmon/` (PresentMon 2.6.0 portable, exe gitignored) +
  `tools/collect_shadow.py --fps-file/--fps-process/--fps-reload` + `tools/fps_join.py` (offline backfill).
  PresentMon locks its CSV while recording, so the join is post-capture; smoke labelled 16/16 rows
  (fps 45.5-178.0, p95 6.0-6.1ms, fixed -28796.9s clock offset). See `docs/p4-gate-report.md` §3.

## 6. Gate to phase-04-done (OPEN)
- [ ] Real D_safe >=2000, 9-grid >=80%, interactive >=15%, 1 plug event.
  - r27: rows 48753 (numerically OK) but grid 3/16 (W0/W1/W2 AC only), interactive 0.142, plug 0.
- [ ] Real Return +10% vs B2 anchor, shield not up (needs E4/E5 live + perf labels).
  - r27: synth BO +1.3%, B2 proxy anchor 71.4; perf chain ready, live still gate-locked.
- [ ] E4 shadow gate (>=8h valid coverage: game>=2h + office>=2h + idle>=1h + >=1 plug event).
  - r28: **shadow-run link implemented** — `tools/shadow_run.py` (sensing + stub policy + fence trial +
    BlackBox 12 fields + L2 dry-run only, real AC/DC via GetSystemPowerStatus, powercfg scheme as the
    in-service signal) + `tools/e4_shadow_report.py` (four criteria + coverage matrix + open_items).
    Smoke: 10/10 BlackBox complete, 0 errors, 0 budget overruns, fence OK x10 (0.0103ms);
    c1 `FAIL agreement_rate 0.0` once calibrated via `--gear-map` (shadow suggests Balance, in-service is
    节能/Quiet), c2 PASS (L2+ = 0), c3 BLOCKED (no frames), c4 PASS, `e4_ready=false`.
  - r27 gap matrix still open: idle 9.71h OK; office 1.92h / game 1.92h (each ~5 min short); plug 0.
    Remaining unlocks: Fn+Q calibration walk (c1), PresentMon same-window run (c3), W1/W2 + DC + real plug.
  - Known limit: no CPU temperature channel pre-E5 -> fence fed a labelled GPU proxy; live stays LOCKED.
- [ ] Freeze D_safe as P6 replay buffer snapshot + tag.
