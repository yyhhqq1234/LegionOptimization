# P4 Evidence Index (acceptance -> evidence)

> Objective: D_safe>=2000/machine 9-grid>=80% + 3-model + replay Return+10% shield-flat + ONNXv1 <10MB <5ms + tag phase-04-done.
> Legend: DONE-syn = synthetic pipeline proof; OPEN = needs operator/wall-time/live.

## 1. D_safe scale (OPEN, collecting)
- Synth A 2000 16/16 (`samples/D_safe_synth_A_v1.csv`, `tools/make_dsafe_synth.py`).
- Synth B 1200 hetero (`samples/D_safe_synth_B_v1.csv`, `tools/make_dsafe_synth_B.py`).
- Real: part1 508 + part2 growing + locked-file (~1676 incl 70 misaligned declared), W0/AC only, coverage 1/16 (`tools/collect_shadow.py`, `tools/coverage_report.py`, `tools/repair_shadow.py`).
- Missing: W1-W7 x AC/DC rotation, 1 plug event (`tools/plug_watch.py` ready), perf labels (`fps/p95` reserved, presentmon absent).

## 2. Three-model compare (DONE-syn)
- MLP val 0.08, RMSE 3.23/2.94/1.74, tau 0.815; LGB 2.88/2.11/1.70 (honest: LGB wins on synth); ENS undertrained.
- Report `samples/p4_full_compare.json` + `samples/p4_synth_compare.json`; code `tools/train_p4_full.py`, `src/policy/surrogate.py`.
- Cross-machine A->B RMSE 3.33/2.66/1.74 vs same-A 3.10/2.69/1.66 (`samples/cross_AB.json`, `tools/cross_AB_synth.py`).
- Real pilot 600 rows: power 0.19 beats mean 0.26, temp flat honest, perf head blocked (`samples/real_pilot.json`, `tools/pilot_real_train.py`).

## 3. Replay Return+10% shield-flat (OPEN)
- Synth raw -7.6%, BO-constrained +1.3% shield-flat (`samples/bo_synth_result.json`, `tools/bo_p4_synth.py`).
- V12 B2 anchor proxy mean 71.4 p50 74.9 (B0/B1/B2 logs missing, frozen-config x surrogate, `samples/reward_baseline_B2.csv`, `tools/reward_baseline_B2.py`).
- B2 four-gear dry-run 4/4 OK violation 0 (`samples/envelope_B2_dryrun.json`).
- Blocked: real multi-grid + perf labels + small-step live (E4/E5 gate; user small-step confirm logged, gate missing -> live LOCKED).

## 4. ONNX v1 (DONE-syn)
- `samples/predictor_v1.onnx` (+`.data`) 0.02MB, CPU 0.02ms (PASS <10MB <5ms). Deps locked: lightgbm 4.7.0, onnx 1.23.0, onnxscript (`requirements.txt`).

## 5. Protocols/tools (DONE)
- `docs/p4-collection-protocol.md` (15% interactive, 9-grid quota, small-step rule).
- `tools/interactive_probe.py` (cold 608ms / hot 88ms verified), `tools/plug_watch.py` (status2/95pct).
- Shadow pilot `samples/shadow_pilot.json`, `samples/selfcheck_V01-V03.json`, `samples/state48_report_V04-V06.csv`, `samples/action_dryrun_V07-V09.log`.

## 6. Gate to phase-04-done (OPEN)
- [ ] Real D_safe >=2000, 9-grid >=80%, interactive >=15%, 1 plug event.
- [ ] Real Return +10% vs B2 anchor, shield not up (needs E4/E5 live + perf labels).
- [ ] Freeze D_safe as P6 replay buffer snapshot + tag.
