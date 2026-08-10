using System;
using System.Threading.Tasks;
using LenovoLegionToolkit.Lib.Controllers;
using LenovoLegionToolkit.Lib.System.Management;
using LenovoLegionToolkit.Lib.Utils;

namespace LenovoLegionToolkit.Lib.Listeners;

public class ThermalModeListener(
    WindowsPowerModeController windowsPowerModeController,
    WindowsPowerPlanController windowsPowerPlanController)
    : AbstractWMIListener<ThermalModeListener.ChangedEventArgs, ThermalModeState, int>(WMI.LenovoGameZoneThermalModeEvent.Listen)
{
    public class ChangedEventArgs(ThermalModeState state) : EventArgs
    {
        public ThermalModeState State { get; } = state;
    }

    private readonly ThreadSafeCounter _suppressCounter = new();

    protected override ThermalModeState GetValue(int value)
    {
        // Handle both sequential (1,2,3,4) and non-sequential (1,2,3,224,255) WMI numbering
        // ThermalModeState enum: Quiet=1, Balance=2, Performance=3, Extreme=224, GodMode=255
        var state = value switch
        {
            1 => ThermalModeState.Quiet,
            2 => ThermalModeState.Balance,
            3 => ThermalModeState.Performance,
            4 => ThermalModeState.Extreme,       // Sequential WMI numbering (e.g. Y7000 2025 IAX10)
            224 => ThermalModeState.Extreme,      // Non-sequential WMI numbering
            255 => ThermalModeState.GodMode,      // Non-sequential WMI numbering
            _ => (ThermalModeState)value
        };

        if (!Enum.IsDefined(state))
        {
            Log.Instance.Trace($"Unknown value received: {value}");

            state = ThermalModeState.Unknown;
        }

        return state;
    }

    protected override ChangedEventArgs GetEventArgs(ThermalModeState value) => new(value);

    protected override async Task OnChangedAsync(ThermalModeState state)
    {
        if (!_suppressCounter.Decrement())
        {
            Log.Instance.Trace($"Suppressed.");
            return;
        }

        if (state == ThermalModeState.Unknown)
            return;

        var powerModeState = state switch
        {
            ThermalModeState.Quiet => PowerModeState.Quiet,
            ThermalModeState.Balance => PowerModeState.Balance,
            ThermalModeState.Performance => PowerModeState.Performance,
            ThermalModeState.Extreme => PowerModeState.Extreme,
            ThermalModeState.GodMode => PowerModeState.GodMode,
            _ => throw new ArgumentOutOfRangeException(nameof(state), state, null)
        };

        await windowsPowerModeController.SetPowerModeAsync(powerModeState).ConfigureAwait(false);
        await windowsPowerPlanController.SetPowerPlanAsync(powerModeState).ConfigureAwait(false);
    }

    public void SuppressNext()
    {
        Log.Instance.Trace($"Suppressing next...");

        _suppressCounter.Increment();
    }
}
