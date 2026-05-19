import numpy as np
import os, re
from typing import List, Optional
from dataclasses import dataclass
import pyCAPS as pycaps

@dataclass
class AirfoilPolar:
    name: str
    alpha: np.ndarray
    cl: np.ndarray
    cd: np.ndarray
    cm: np.ndarray
    cdp: Optional[np.ndarray] = None
    xtr_top: Optional[np.ndarray] = None
    xtr_bot: Optional[np.ndarray] = None
    reynolds: Optional[float] = None
    mach: Optional[float] = None

    def cl_cd(self):
        cd_safe = np.where(self.cd <= 0, np.nan, self.cd)
        return self.cl / cd_safe

    def max_l_over_d(self):
        ratios = self.cl_cd()
        return np.nanmax(ratios)

    def stall_angle(self):
        if self.cl.size == 0:
            return np.nan, np.nan
        idx = int(np.nanargmax(self.cl))
        return self.alpha[idx], self.cl[idx]

_HEADER_RE = re.compile(r"^\s*alpha\b", re.IGNORECASE)
_RE_MACH_RE = re.compile(r"Re\s*=\s*([0-9.eE+-]+).*?(?:Mach|Ma)\s*=\s*([0-9.eE+-]+)")

def parse_xfoil_polar(filepath: str) -> AirfoilPolar:
    name = os.path.basename(filepath).rsplit('.', 1)[0]

    alpha: List[float] = []
    cl: List[float] = []
    cd: List[float] = []
    cdp: List[float] = []
    cm: List[float] = []
    xt: List[float] = []
    xb: List[float] = []

    reynolds = None
    mach = None
    in_data = False

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue

            # Try to capture Re and Mach from header lines
            if reynolds is None or mach is None:
                m = _RE_MACH_RE.search(s)
                if m:
                    try:
                        reynolds = float(m.group(1))
                        mach = float(m.group(2))
                    except ValueError:
                        pass

            # Detect data header row and start parsing after it
            if _HEADER_RE.match(s):
                in_data = True
                continue
            if not in_data:
                # Some PACC files don't have the explicit header; fall back to numeric parse
                # when we first hit a line with >=7 numeric columns.
                parts = s.split()
                if len(parts) >= 7:
                    try:
                        [float(p) for p in parts[:7]]
                        in_data = True
                    except ValueError:
                        continue
                else:
                    continue

            parts = s.split()
            # Expected columns: alpha CL CD CDp CM Top_Xtr Bot_Xtr
            if len(parts) < 7:
                continue
            try:
                a  = float(parts[0])
                clv = float(parts[1])
                cdv = float(parts[2])
                cdpv = float(parts[3])
                cmv = float(parts[4])
                xtv = float(parts[5])
                xbv = float(parts[6])
            except ValueError:
                continue

            alpha.append(a); cl.append(clv); cd.append(cdv); cdp.append(cdpv); cm.append(cmv)
            xt.append(xtv); xb.append(xbv)

    # If header didn’t contain Re/Mach, try filename hint like *_Re1e6_* or *_Re1000000_*
    if reynolds is None:
        m = re.search(r"[Rr]e[_=]?([0-9.eE+-]+)", name)
        if m:
            try:
                reynolds = float(m.group(1))
            except ValueError:
                pass

    # Convert to arrays and sort by alpha (drop duplicate alphas)
    A = np.array(alpha, dtype=float)
    CL = np.array(cl, dtype=float)
    CD = np.array(cd, dtype=float)
    CDP = np.array(cdp, dtype=float) if cdp else None
    CM = np.array(cm, dtype=float)
    XT = np.array(xt, dtype=float) if xt else None
    XB = np.array(xb, dtype=float) if xb else None

    if A.size:
        order = np.argsort(A)
        A, CL, CD, CM = A[order], CL[order], CD[order], CM[order]
        if CDP is not None: CDP = CDP[order]
        if XT is not None: XT = XT[order]
        if XB is not None: XB = XB[order]
        # Deduplicate by alpha if any repeats
        uniq, idx = np.unique(A, return_index=True)
        A, CL, CD, CM = A[idx], CL[idx], CD[idx], CM[idx]
        if CDP is not None: CDP = CDP[idx]
        if XT is not None: XT = XT[idx]
        if XB is not None: XB = XB[idx]

    return AirfoilPolar(
        name=name, alpha=A, cl=CL, cd=CD, cm=CM,
        cdp=CDP, xtr_top=XT, xtr_bot=XB,
        reynolds=reynolds, mach=mach
    )

def load_all_polars(directory: str) -> List[AirfoilPolar]:
    polars: List[AirfoilPolar] = []
    for file in sorted(os.listdir(directory)):
        if file.lower().endswith(".txt"):
            path = os.path.join(directory, file)
            try:
                polars.append(parse_xfoil_polar(path))
            except Exception as e:
                print(f"Failed to load {file}: {e}")
    return polars
