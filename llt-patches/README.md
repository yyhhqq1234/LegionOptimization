# LLT Source Patches

These are the 3 modified files from Lenovo Legion Toolkit source that enable full Fn+Q support on Lenovo Legion laptops where the 4th mode (超能/Extreme) doesn't fire `LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT`.

## Changes

### 1. `Listeners/PowerModeListener.cs`
- `GetValue()`: Added WMI value `4 → PowerModeState.Extreme` mapping
- Supports both sequential (1,2,3,4) and non-sequential (1,2,3,224,255) WMI numbering

### 2. `Listeners/ThermalModeListener.cs`
- `GetValue()`: Added WMI value `4 → ThermalModeState.Extreme` mapping
- Supports both sequential and non-sequential WMI numbering

### 3. `Automation/AutomationProcessor.cs`
- Added `ThermalModeListener` to constructor and `InitializeAsync` subscription
- Added `ThermalModeListener_Changed` handler that maps `ThermalModeState → PowerModeState → PowerModeAutomationEvent`
- This ensures automation pipelines trigger even when only the thermal mode event fires

## Upstream

These files are from: https://github.com/BartoszCichecki/LenovoLegionToolkit

The full source tree is NOT included in this repo. Clone upstream, apply these patches, and rebuild:
```
git clone https://github.com/BartoszCichecki/LenovoLegionToolkit
cd LenovoLegionToolkit
# Copy the 3 modified files to their respective locations
# Build with: dotnet build -c Release
```
