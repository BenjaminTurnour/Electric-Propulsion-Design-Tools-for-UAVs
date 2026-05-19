# aero_utils/xfoil_api.py
import shutil, subprocess, tempfile, sys
from pathlib import Path
from typing import Iterable
from .xfoil_parser import parse_xfoil_polar

def _run(exe: str, script: str, cwd: Path, timeout: int) -> str:
    """Run xfoil with a given multi-line script; return full stdout."""
    if not script.endswith("\n"):
        script += "\n"
    proc = subprocess.run(
        [exe],
        input=script.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        cwd=str(cwd),
    )
    return proc.stdout.decode(errors="ignore")

def get_polar_naca(
    naca: str = "2412",
    alphas: Iterable[float] = range(-6, 17, 1),
    Re: float = 1e6,
    Mach: float = 0.0,
    Ncrit: float = 9.0,
    iter_limit: int = 200,
    timeout: int = 180,
    save_to: bool = False,
    save_filename: str | None = None,
):
    """
    Run XFoil in batch to generate a polar for a NACA airfoil.
    - No input geometry files (uses NACA generator).
    - Always recomputes (no caching).
    - Writes to a temp file, parses it, returns AirfoilPolar.
    - If save_to=True, copies raw polar to '<script_dir>/polars/<name>.txt'.
    """
    exe = shutil.which("xfoil")
    if not exe:
        raise FileNotFoundError("xfoil not found on PATH (WSL: sudo apt install -y xfoil)")

    code = str(naca).lower().replace("naca", "").strip()
    a_list = alphas.tolist() if hasattr(alphas, "tolist") else list(alphas)
    a_list = sorted(float(a) for a in a_list)

    # Use ASEQ only if step is uniform (avoids precision gotchas)
    use_aseq = (
        len(a_list) >= 3
        and abs((a_list[1] - a_list[0]) - (a_list[-1] - a_list[-2])) < 1e-12
    )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        out_file = td_path / "polar.out"   # relative filename is most reliable

        # ---------------------------
        # Attempt 1: PACC with filename
        # ---------------------------
        s1 = []
        s1 += [f"NACA {code}"]
        s1 += ["PANE"]
        s1 += ["OPER"]
        s1 += [f"ITER {iter_limit}"]
        if Mach and Mach > 0:
            s1 += [f"MACH {Mach}"]
        # Turn on viscous at desired Re
        s1 += [f"VISC {Re}"]
        # Enter VPAR submenu, set Ncrit, then BLANK to exit back to OPER
        s1 += ["VPAR", f"N {Ncrit}", ""]
        # Start accumulation (answer BOTH prompts: filename, then blank dump)
        s1 += ["PACC", out_file.name, ""]
        # Alpha sweep
        if use_aseq:
            a0, a1, da = a_list[0], a_list[-1], (a_list[1] - a_list[0])
            s1 += [f"ASEQ {a0} {a1} {da}"]
        else:
            for a in a_list:
                s1 += [f"ALFA {a}"]
        # Stop accumulation (two blanks), leave OPER (blank), then quit
        s1 += ["PACC", "", ""]
        s1 += ["", "QUIT"]
        log1 = _run(exe, "\n".join(s1) + "\n", td_path, timeout)

        if not out_file.exists():
            # ---------------------------
            # Attempt 2 (fallback): accumulate with no files, then PWRT
            # ---------------------------
            s2 = []
            s2 += [f"NACA {code}"]
            s2 += ["PANE"]
            s2 += ["OPER"]
            s2 += [f"ITER {iter_limit}"]
            if Mach and Mach > 0:
                s2 += [f"MACH {Mach}"]
            s2 += [f"VISC {Re}"]
            s2 += ["VPAR", f"N {Ncrit}", ""]
            # Start accumulation with NO files (answer both prompts blank)
            s2 += ["PACC", "", ""]
            if use_aseq:
                a0, a1, da = a_list[0], a_list[-1], (a_list[1] - a_list[0])
                s2 += [f"ASEQ {a0} {a1} {da}"]
            else:
                for a in a_list:
                    s2 += [f"ALFA {a}"]
            # Explicitly write the polar
            s2 += ["PWRT", out_file.name]
            # Tidy: stop accumulation, leave OPER, then quit
            s2 += ["PACC", "", ""]
            s2 += ["", "QUIT"]
            log2 = _run(exe, "\n".join(s2) + "\n", td_path, timeout)

            if not out_file.exists():
                raise RuntimeError(
                    "XFoil did not produce a polar file.\n"
                    "--- Attempt 1 log ---\n" + log1 +
                    "\n--- Attempt 2 log ---\n" + log2
                )

        # Parse and finalize dataclass
        polar = parse_xfoil_polar(str(out_file))
        if polar.reynolds is None:
            polar.reynolds = Re
        if polar.mach is None:
            polar.mach = Mach
        polar.name = f"naca{code}_Re{int(Re)}_Ma{Mach:.2f}_Nc{Ncrit:.1f}"

        # Optional save beside the calling script
        if save_to:
            script_dir = Path(sys.argv[0]).resolve().parent
            dest_dir = script_dir / "polars"
            dest_dir.mkdir(parents=True, exist_ok=True)
            fname = save_filename or f"{polar.name}.txt"
            dest = dest_dir / fname
            dest.write_text(out_file.read_text())
            setattr(polar, "saved_path", str(dest))

        return polar
