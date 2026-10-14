"""Lenovo GameZone ACPI-WMI read-only sensing (P4 r29).

Background: Fn+Q gear switching does NOT change the Windows power scheme on this box
(measured: the scheme stayed "节能" while the machine was in Beast mode), so the r28
scheme-based signal is unusable. LENOVO_GAMEZONE_DATA instead exposes out-parameter
class methods that answer with the real machine state when called with EMPTY arguments
(passing Data explicitly returns "invalid parameter" -- the parameter is qualifier out).

Measured on Y7000 2025 (U7 255HX, driver 617.14):
    GetThermalMode()     -> 3        # operator confirmed the machine was in Beast mode
    GetSmartFanMode()    -> 3
    GetProductInfo()     -> 100
    GetVersion()         -> 17
    GetCpuFrequency()    -> 340792400  (10 kHz units -> ~3.41 GHz)
    GetPowerChargeMode() -> 1
    GetCPUTemp()         -> 0        # 0 = not provided by ACPI here, NOT a temperature
    GetGPUTemp()         -> 0

Only Get* / Is* methods are exposed. No Set* method exists in this module and none must
ever be added: actuation stays in the L2 layer behind the E4/E5 gate.
"""
import subprocess

CLASS = "LENOVO_GAMEZONE_DATA"
NAMESPACE = "root\\WMI"
_PS_TIMEOUT_S = 15

# mode value -> gear name. Only 3 = Beast is confirmed by the operator so far; the rest
# must come from a Fn+Q calibration walk (tools/gear_probe.py). Unknown modes are
# reported raw and left unmapped instead of being guessed.
MODE_TO_GEAR = {3: "Beast"}
GEAR_TO_MODE = {v: k for k, v in MODE_TO_GEAR.items()}

_SVC = None
_COM_FAILED = False


def _service():
    """Cached WbemScripting service (COM is ~ms; the powershell path is a fallback)."""
    global _SVC, _COM_FAILED
    if _SVC is not None or _COM_FAILED:
        return _SVC
    try:
        import win32com.client
        loc = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        _SVC = loc.ConnectServer(".", NAMESPACE)
    except Exception:
        _COM_FAILED = True
        _SVC = None
    return _SVC


def _ps_call(method):
    ps = (f"$i=Get-CimInstance -Namespace root/WMI -ClassName {CLASS};"
          f"(Invoke-CimMethod -InputObject $i -MethodName {method} -Arguments @{{}}).Data")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=_PS_TIMEOUT_S)
        out = (r.stdout or "").strip()
        return int(out) if out.lstrip("-").isdigit() else None
    except Exception:
        return None


def _call(method):
    """Call one out-parameter method with empty args; return int or None."""
    svc = _service()
    if svc is not None:
        try:
            in_params = svc.Get(CLASS).Methods_(method).InParameters.SpawnInstance_()
            out = svc.ExecMethod_(CLASS, method, in_params)
            v = out.Properties_("Data").Value
            return int(v) if v is not None else None
        except Exception:
            return _ps_call(method)
    return _ps_call(method)


def read_thermal_mode():
    """Raw mode integer (None when unavailable). 3 = Beast on this box."""
    return _call("GetThermalMode")


def read_gear():
    """(gear_name_or_None, raw_mode) - unmapped modes come back raw, never guessed."""
    mode = read_thermal_mode()
    if mode is None:
        return None, None
    return MODE_TO_GEAR.get(mode), mode


def read_cpu_freq_ghz():
    v = _call("GetCpuFrequency")
    return round(v / 1e8, 3) if v else None        # 10 Hz units -> GHz (340792400 -> 3.408)


def read_product_info():
    return _call("GetProductInfo")


def read_power_charge_mode():
    return _call("GetPowerChargeMode")


def read_all():
    """Snapshot of every read-only value this module exposes."""
    return {"thermal_mode": read_thermal_mode(), "smart_fan_mode": _call("GetSmartFanMode"),
            "cpu_freq_ghz": read_cpu_freq_ghz(), "product_info": read_product_info(),
            "version": _call("GetVersion"), "power_charge_mode": read_power_charge_mode(),
            "cpu_temp_datum": _call("GetCPUTemp"), "gpu_temp_datum": _call("GetGPUTemp"),
            "ac_fit_for_oc": _call("IsACFitForOC")}
