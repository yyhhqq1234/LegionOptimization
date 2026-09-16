"""MSR 只读探针（P1 Step 1-3）：经 WinRing0 读 IA32_TEMPERATURE_TARGET。

只读保证：仅发送 OLS READ_MSR DeviceIoControl；不写任何 MSR，
不改驱动/系统状态。驱动生命周期（sc start/stop）由调用者在外部管理，
本脚本只 open → read → close。

用法（评估流程，需管理员终端）：
  sc.exe start WinRing0_1_2_0
  python probe/msr_read.py
  sc.exe stop WinRing0_1_2_0
"""

import ctypes
import struct
import sys
from ctypes import wintypes

DEVICE = r"\\.\WinRing0_1_2_0"
# OLS CTL_CODE(0x9C40, 0x821, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_READ_MSR = 0x9C402084

MSR_TEMP_TARGET = 0x1A2  # EAX[22:16] = TJMax
MSR_THERM_STATUS = 0x19C  # bit31 valid；EAX[22:16] = 距 TJMax 偏移（交叉验证）

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                            wintypes.HANDLE]
k32.CreateFileW.restype = wintypes.HANDLE
k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.DeviceIoControl.restype = wintypes.BOOL


def read_msr(handle, index):
    outbuf = ctypes.create_string_buffer(8)
    n = wintypes.DWORD(0)
    ok = k32.DeviceIoControl(handle, IOCTL_READ_MSR,
                             struct.pack("<I", index), 4,
                             outbuf, 8, ctypes.byref(n), None)
    if not ok:
        raise OSError(f"READ_MSR 0x{index:X} failed, gle={ctypes.get_last_error()}")
    return struct.unpack("<II", outbuf.raw)


def main():
    h = k32.CreateFileW(DEVICE, 0x80000000, 0, None, 3, 0, None)  # GENERIC_READ
    if not h:
        print(f"FAIL open {DEVICE} gle={ctypes.get_last_error()} (driver not loaded?)")
        return 1
    try:
        eax, _ = read_msr(h, MSR_TEMP_TARGET)
        tjmax = (eax >> 16) & 0xFF
        print(f"MSR 0x1A2 EAX=0x{eax:08X} TJMax={tjmax}C")
        eax2, _ = read_msr(h, MSR_THERM_STATUS)
        valid = bool(eax2 & 0x80000000)
        readout = (eax2 >> 16) & 0x7F
        print(f"MSR 0x19C EAX=0x{eax2:08X} valid={valid} "
              f"readout={readout} pkg~{tjmax - readout}C")
        if not (60 <= tjmax <= 125):
            print("WARN TJMax outside plausible range; record raw, investigate")
            return 2
        return 0
    finally:
        k32.CloseHandle(h)


if __name__ == "__main__":
    sys.exit(main())
