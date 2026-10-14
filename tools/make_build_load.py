"""Generate the W3 compile-load project (460 C# compilation units) under artifacts/build_load.

The generated sources are ~3.6MB of filler, so only this generator is committed; regenerate with:

    python tools/make_build_load.py
    dotnet build artifacts/build_load/app/app.csproj -t:Rebuild -m:8      # the actual load

Measured calibration on this box (255HX, 28 threads):
    60 units  + plain `dotnet build -t:Rebuild` loop  -> 0.23 cores / 7.1% CPU  (too weak: the
              loop mostly pays dotnet CLI start/stop, not compilation)
    460 units + `-m:8`                                -> 5.67 cores / 37.4% CPU (usable compile load)

Verify any rerun with the two independent reads: the Get-Process CPU-time delta divided by the
sample seconds gives cores used, and Get-Counter '\\Processor(_Total)\\% Processor Time' should
agree. A CPU-bound cell collected below ~30 percent is not a compile cell, it is process churn.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJ = ROOT / "artifacts" / "build_load" / "app"
UNITS = 460
METHODS = 200


def main():
    PROJ.parent.mkdir(parents=True, exist_ok=True)
    if not (PROJ / "app.csproj").exists():
        subprocess.run(["dotnet", "new", "console", "-o", str(PROJ), "--force"],
                       check=False, stdout=subprocess.DEVNULL)
    for i in range(1, UNITS + 1):
        lines = ["namespace app {", "  public class C%d {" % i]
        for j in range(1, METHODS + 1):
            lines.append("    public int M%d(int x) => x * %d + %d;" % (j, i, j))
        lines += ["  }", "}"]
        (PROJ / ("C%d.cs" % i)).write_text("\n".join(lines), encoding="ascii")
    n = len(list(PROJ.glob("C*.cs")))
    kb = sum(p.stat().st_size for p in PROJ.glob("C*.cs")) / 1024
    print(f"generated {n} C# units ({kb:.0f} KB) under {PROJ.relative_to(ROOT)}")
    print("run the load:  dotnet build artifacts/build_load/app/app.csproj -t:Rebuild -m:8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
