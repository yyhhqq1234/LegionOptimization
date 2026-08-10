using System;
using System.Threading.Tasks;
using LenovoLegionToolkit.Lib.Controllers;
using LenovoLegionToolkit.Lib.Controllers.GodMode;
using LenovoLegionToolkit.Lib.Extensions;
using LenovoLegionToolkit.Lib.Messaging;
using LenovoLegionToolkit.Lib.Messaging.Messages;
using LenovoLegionToolkit.Lib.System.Management;
using LenovoLegionToolkit.Lib.Utils;

namespace LenovoLegionToolkit.Lib.Listeners;

public class PowerModeListener(
    GodModeController godModeController,
    WindowsPowerModeController windowsPowerModeController,
    WindowsPowerPlanController windowsPowerPlanController)
    : AbstractWMIListener<PowerModeListener.ChangedEventArgs, PowerModeState, int>(WMI.LenovoGameZoneSmartFanModeEvent.Listen), INotifyingListener<PowerModeListener.ChangedEventArgs, PowerModeState>
{
    public class ChangedEventArgs(PowerModeState state) : EventArgs
    {
        public PowerModeState State { get; } = state;
    }

    protected override PowerModeState GetValue(int value)
    {
        // Handle both sequential (1,2,3,4) and non-sequential (1,2,3,224,255) WMI numbering
        // PowerModeState enum: Quiet=0, Balance=1, Performance=2, Extreme=223, GodMode=254
        return value switch
        {
            1 => PowerModeState.Quiet,
            2 => PowerModeState.Balance,
            3 => PowerModeState.Performance,
            4 => PowerModeState.Extreme,       // Sequential WMI numbering (e.g. Y7000 2025 IAX10)
            224 => PowerModeState.Extreme,      // Non-sequential WMI numbering
            255 => PowerModeState.GodMode,      // Non-sequential WMI numbering
            _ => (PowerModeState)(value - 1)    // Fallback for unknown values
        };
    }

    protected override ChangedEventArgs GetEventArgs(PowerModeState value) => new(value);

    protected override async Task OnChangedAsync(PowerModeState value)
    {
        await ChangeDependenciesAsync(value).ConfigureAwait(false);
        PublishNotification(value);
    }

    public async Task NotifyAsync(PowerModeState value)
    {
        await ChangeDependenciesAsync(value).ConfigureAwait(false);
        RaiseChanged(value);
    }

    protected override async Task<bool> CanStartAsync()
    {
        var mi = await Compatibility.GetMachineInformationAsync().ConfigureAwait(false);
        return Compatibility.IsLegion(mi.LegionSeries);
    }

    private async Task ChangeDependenciesAsync(PowerModeState value)
    {
        if (value is PowerModeState.GodMode)
            await godModeController.ApplyStateAsync().ConfigureAwait(false);

        await windowsPowerModeController.SetPowerModeAsync(value).ConfigureAwait(false);
        await windowsPowerPlanController.SetPowerPlanAsync(value).ConfigureAwait(false);
    }

    private static void PublishNotification(PowerModeState value)
    {
        switch (value)
        {
            case PowerModeState.Quiet:
                MessagingCenter.Publish(new NotificationMessage(NotificationType.PowerModeQuiet, value.GetDisplayName()));
                break;
            case PowerModeState.Balance:
                MessagingCenter.Publish(new NotificationMessage(NotificationType.PowerModeBalance, value.GetDisplayName()));
                break;
            case PowerModeState.Performance:
                MessagingCenter.Publish(new NotificationMessage(NotificationType.PowerModePerformance, value.GetDisplayName()));
                break;
            case PowerModeState.Extreme:
                MessagingCenter.Publish(new NotificationMessage(NotificationType.PowerModeExtreme, value.GetDisplayName()));
                break;
            case PowerModeState.GodMode:
                MessagingCenter.Publish(new NotificationMessage(NotificationType.PowerModeGodMode, value.GetDisplayName()));
                break;
        }
    }
}
