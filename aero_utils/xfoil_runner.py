# batch XFoil runner
import shutil, subprocess, os
from pathlib import Path

def run_xfoil_polar_file(
    airfoil_source: str,    # path to .dat or 'naca 2412'
    alphas: list[float],
    Re: float,
    Mach: float = 0.0,
    Ncrit: float = 9.0,
    iter_limit: int = 200,
    out_path: str = "polars/polar.txt",
    timeout: int = 180,
) -> str:
    """
    Runs XFoil in batch and writes a PACC polar file at out_path.
    Returns the captured stdout/stderr text for logging.
    """
    exe = shutil.which("xfoil")
    if not exe:
        raise FileNotFoundError("xfoil not found on PATH. On WSL: `sudo apt install -y xfoil`.")

    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # build command script
    lines = []
    if airfoil_source.lower().startswith("naca "):
        lines += [airfoil_source]
    else:
        lines += [f"LOAD {airfoil_source}"]
    lines += ["PANE", "OPER", f"ITER {iter_limit}"]
    if Mach and Mach > 0: lines += [f"MACH {Mach}"]
    lines += [f"VISC {Re}", f"VPAR N {Ncrit}", "PACC", out_path, ""]
    for a in alphas: lines += [f"ALFA {a}"]
    lines += ["PACC", "", "QUIT"]
    script = "\n".join(lines)

    proc = subprocess.run([exe],
                          input=script.encode(),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=os.getcwd(),
                          timeout=timeout)
    return proc.stdout.decode(errors="ignore")
