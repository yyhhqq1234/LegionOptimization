# LegionOptimization

Lenovo Legion laptop Fn+Q power mode CPU tuning automation — applies custom frequency caps, FIVR undervolt, and power limits per power mode via Lenovo Legion Toolkit automation + ThrottleStop.

## Hardware

- **Tested on**: Lenovo Y7000 2025 IAX10 (Core Ultra 7 255HX / Arrow Lake-HX / RTX 5060 Laptop)
- **Should work on**: Any Lenovo Legion with Fn+Q power modes and ThrottleStop-compatible CPU

## Per-Mode Settings

| Mode | Max Freq | Undervolt (Core+P-Cache) | PL1 |
|------|----------|--------------------------|-----|
| Quiet (安静) | 3.8 GHz | -70 mV | 25 W |
| Balance (均衡) | 4.8 GHz | -65 mV | 40 W |
| Beast (野兽) | 5.0 GHz | -55 mV | 65 W |
| Extreme (超能) | 5.2 GHz | -45 mV | 65 W |

GPU is left at default. FIVR injection is fire-and-forget (ThrottleStop starts → injects MSR → killed after 5s).

## Architecture

```
Fn+Q press
  ├─ Quiet/Balance/Beast → LLT Automation (PowerModeAutomationPipelineTrigger)
  │    → quiet.bat / balance.bat / beast.bat
  └─ Extreme/超能 → PowerModeWatcher.ps1 (LENOVO_GAMEZONE_THERMAL_MODE_EVENT)
       → custom.bat

Each batch script:
  1. Kill ThrottleStop
  2. Copy profile INI → ThrottleStop.ini
  3. powercfg set CPU frequency cap
  4. Launch ThrottleStop (no UAC via scheduled task)
  5. Wait 5s for FIVR injection
  6. Kill ThrottleStop

Boot chain:
  Logon → LegionLLT task → start_llt.bat → LLT (system tray) + PowerModeWatcher.ps1
  Logon +30s → LegionProfile task → startup_inject.bat → initial FIVR injection
```

## Why a separate WMI watcher for Extreme mode?

On some hardware (e.g., Y7000 2025 IAX10), `LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT` only fires for the first 3 Fn+Q positions. The 4th position (超能/Extreme) only fires `LENOVO_GAMEZONE_THERMAL_MODE_EVENT` with mode=224. `PowerModeWatcher.ps1` independently monitors the thermal mode event to catch this.

LLT's `ThermalModeListener` already receives this event, but the stock LLT code only uses it to set the Windows power plan — it doesn't publish to the automation messaging system. Our patched LLT build (`llt-build/`) adds this hook. Source patches are in `llt-patches/`.

## Setup

### 1. Install location
Clone/extract to **`D:\LegionOptimization`** (required — automation.json paths use this).

To install elsewhere, run `configure.bat` after setup to update the paths in LLT's automation.json.

### 2. One-time setup (run as Administrator)
```bat
setup_startup.bat
```

This creates 3 scheduled tasks:
- `LegionLLT` — Launches LLT + watcher at logon
- `LegionProfile` — Initial FIVR injection at logon (+30s delay)
- `ThrottleStop_NoUAC` — Lets batch scripts launch ThrottleStop without UAC prompts

### 3. Import automation into LLT
1. Open Lenovo Legion Toolkit
2. Settings → Automation → Import
3. Select `automation.template.json`
4. Run `configure.bat` (as admin) to update paths
5. Enable automation in LLT

### 4. Verify
1. Reboot
2. LLT should appear in system tray
3. Press Fn+Q to cycle through modes
4. ThrottleStop should briefly appear (MiniMode) then close for each switch
5. Check `switch_log.txt` for execution log

## Porting to Another Legion Laptop

1. Copy the entire `LegionOptimization` folder to `D:\LegionOptimization`
2. Adjust the undervolt and frequency values in `ThrottleStop_profiles/*.ini` and `*.bat` for your CPU
3. Run `setup_startup.bat` as Administrator
4. In LLT, import automation and run `configure.bat`

### Adjusting for your CPU

- **Frequency caps**: Edit `powercfg /setacvalueindex ... XXXX` lines in each `.bat` file
- **Undervolt values**: Edit FIVR voltage encodings in `ThrottleStop_profiles/*.ini`
  - Voltage encoding: multiply mV by 1.024, convert to hex
  - FIVRVoltageXX = `0xF` + encoded hex, FIVRVoltage2X = P-Cache domain
- **Power limits**: Edit `PowerLimitEAX`/`PowerLimitEDX` in profile INIs

## Files

| File | Purpose |
|------|---------|
| `quiet.bat` / `balance.bat` / `beast.bat` / `custom.bat` | Per-mode switch scripts |
| `PowerModeWatcher.ps1` | WMI watcher for Extreme/超能 mode |
| `start_llt.bat` | LLT + watcher launcher |
| `startup_inject.bat` | Boot-time FIVR injection |
| `setup_startup.bat` | One-time scheduled task creation (run as admin) |
| `configure.bat` | Update automation.json paths for current install |
| `ThrottleStop/` | ThrottleStop portable + ThrottleStop.ini |
| `ThrottleStop_profiles/` | Per-mode INI files |
| `llt-build/` | Pre-built patched LLT |
| `llt-patches/` | Modified LLT source files + build notes |

## Notes

- FIVR MSR values persist after ThrottleStop exits but are lost on reboot
- `SpeedShift=0` in ThrottleStop — frequency control is via Windows power plan (`powercfg`)
- LLT must be closed before running `setup_startup.bat` (it restarts LLT on next logon)
- ThrottleStop window briefly visible in MiniMode during mode switch; this is a TS limitation
