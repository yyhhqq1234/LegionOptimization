# PresentMon (perf labels for shadow collection)

Frame labels (`fps`, `frame_p95_ms`) come from PresentMon 2.6.0. The exe is **not
committed** (`.gitignore: tools/presentmon/*.exe`) — fetch it into this folder once:

```powershell
Invoke-WebRequest -Uri `
 'https://github.com/GameTechDev/PresentMon/releases/download/v2.6.0/PresentMon-2.6.0-x64.exe' `
 -OutFile tools\presentmon\PresentMon-2.6.0-x64.exe
```

Portable exe, no system install (owner machine: ver 2.6.0, RTX 5060 Laptop driver 617.14).

## Constraints found on the owner box (P4 r27)

1. **Recording locks the CSV.** While PresentMon records, a concurrent reader gets
   `[Errno 13] Permission denied`. So capture and labelling are two steps:
   record in parallel, then `tools/fps_join.py` after PresentMon stops.
2. A session named `PresentMon` may already exist (leftover) — pass `--session_name`.
3. `--date_time` carries a constant clock offset on this box (−28796.9s ≈ +8h). The
   joiner rebases onto the shadow's first row and prints the offset; override with
   `--offset` if PresentMon did not start with the collector.
4. `--capture_seconds` does not exist in 2.6.0 — use `--timed <s> --terminate_after_timed`.

## Capture shape (three parts, same window)

```powershell
$pm = '.\tools\presentmon\PresentMon-2.6.0-x64.exe'
$pmcsv = 'artifacts\datasets\pm_<work>_<date>.csv'
Start-Process $pm -ArgumentList '--timed','7200','--session_name','PMW2',
  '--output_file',$pmcsv,'--date_time','--terminate_after_timed','--no_console_stats' `
  -WindowStyle Hidden
python tools\collect_shadow.py --seconds 7200 --work W2 --acdc AC `
  --out artifacts\datasets\D_safe_shadow_A_part5.csv
& $pm --terminate_existing_session --session_name PMW2     # or let --timed end
python tools\fps_join.py --shadow artifacts\datasets\D_safe_shadow_A_part5.csv `
  --pm $pmcsv --process <game.exe>
```

`--process` (joiner `--process`) filters the Application column so `dwm.exe` desktop
composition frames never land in a game/office cell. Rows with no frames in their
±(1.5s/0.5s) window stay empty = honest missing.
