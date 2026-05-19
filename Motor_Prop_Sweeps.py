# sweep_v_t_compute_power_blend_i0safe.py
import sys, os, math
import numpy as np

# Grids to sweep
VELOCITIES_MS = np.linspace(0, 130, 261)   # e.g., 0.5 m/s step
THRUSTS_N     = np.linspace(0, 100, 101)   # e.g., 1 N step

# Debug (prints occasional progress only)
DEBUG = True
PROGRESS_EVERY_VELOCITIES = 20

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
APC_DIR = os.path.join(BASE_DIR, "APC")
OUT_DIR = os.path.join(BASE_DIR, "PropCombos")
if not os.path.isdir(OUT_DIR):
    raise RuntimeError(f"Output folder does not exist: {OUT_DIR}")

# Project imports
from aero_utils.propdata_parser import load_all_propellers
from aero_utils.propdata_interp import build_velocity_slices
from aero_utils.motor_parser import load_motor_models


def sanitize(name: str) -> str:
    # Safe filename
    return "".join(ch if ch not in '<>:"/\\|?* ,' else "_" for ch in name).strip("_")


def prep_bin_interps(bin_data):
    # Prepare sorted arrays for interpolation inside one velocity sample
    need = ("power_w", "rpm", "torque", "thrust")
    if not bin_data or any(k not in bin_data or len(bin_data[k]) == 0 for k in need):
        return None

    pw  = np.asarray(bin_data["power_w"], dtype=float)
    rpm = np.asarray(bin_data["rpm"],      dtype=float)
    tq  = np.asarray(bin_data["torque"],   dtype=float)
    th  = np.asarray(bin_data["thrust"],   dtype=float)

    # Map thrust -> power by sorting on thrust
    idx_t = np.argsort(th)
    th_s  = th[idx_t]
    pw_for_th_s = pw[idx_t]

    # Map power -> rpm/torque by sorting on power
    idx_p = np.argsort(pw)
    pw_s  = pw[idx_p]
    rpm_s = rpm[idx_p]
    tq_s  = tq[idx_p]

    if th_s.size < 2 or pw_s.size < 2:
        return None

    return {
        "th_s": th_s,
        "pw_for_th_s": pw_for_th_s,
        "pw_s": pw_s,
        "rpm_s": rpm_s,
        "tq_s": tq_s,
    }

def eval_bin_at_thrust(bin_interp, thrust_vec):
    # Evaluate one velocity sample at many thrusts
    th_s = bin_interp["th_s"]
    pw_for_th_s = bin_interp["pw_for_th_s"]
    pw_s  = bin_interp["pw_s"]
    rpm_s = bin_interp["rpm_s"]
    tq_s  = bin_interp["tq_s"]

    t = np.asarray(thrust_vec, dtype=float)
    in_range = (t >= th_s[0]) & (t <= th_s[-1])

    p_vec   = np.full_like(t, np.nan, dtype=float)
    rpm_vec = np.full_like(t, np.nan, dtype=float)
    tq_vec  = np.full_like(t, np.nan, dtype=float)

    if not np.any(in_range):
        return p_vec, rpm_vec, tq_vec

    # thrust -> power
    p_in = np.interp(t[in_range], th_s, pw_for_th_s)
    # power -> rpm/torque
    rpm_in = np.interp(p_in, pw_s, rpm_s)
    tq_in  = np.interp(p_in, pw_s, tq_s)

    p_vec[in_range]   = p_in
    rpm_vec[in_range] = rpm_in
    tq_vec[in_range]  = tq_in
    return p_vec, rpm_vec, tq_vec

def no_load_current(v_est, motor):
    """
    Return Io (amps) as a function of estimated terminal voltage v_est.
    Priority:
      1) If motor.no_load_current_A and motor.no_load_test_voltage exist -> scale linearly with V
      2) Else if motor.no_load_current_A exists -> constant amps
      3) Else if motor.no_load_current_AperV exists -> slope * V
      4) Else -> 0
    """
    V = np.asarray(v_est, dtype=float)

    Io_A   = getattr(motor, "no_load_current_A", None)
    V_test = getattr(motor, "no_load_test_voltage", None)
    if Io_A is not None and V_test and V_test > 0:
        return (float(Io_A) / float(V_test)) * V

    if Io_A is not None:
        return np.full_like(V, float(Io_A))

    Io_perV = getattr(motor, "no_load_current_AperV", None)
    if Io_perV is not None:
        return float(Io_perV) * V

    return np.zeros_like(V)


def main():
    # Load props and motors
    props = load_all_propellers(APC_DIR)
    motors = load_motor_models()
    if not props or not motors:
        if DEBUG:
            print("no props or motors loaded")
        return

    # Constants
    TWO_PI = 2.0 * math.pi
    OMEGA_SCALE = TWO_PI / 60.0  # rpm -> rad/s
    V_LIST = np.asarray(VELOCITIES_MS, dtype=float)
    T_LIST = np.asarray(THRUSTS_N, dtype=float)

    if DEBUG:
        print(f"props={len(props)} motors={len(motors)}")
        print(f"v grid: {V_LIST[0]:.2f}..{V_LIST[-1]:.2f} ({len(V_LIST)})")
        print(f"t grid: {T_LIST[0]:.2f}..{T_LIST[-1]:.2f} ({len(T_LIST)})")

    for profile in props:
        # Build velocity samples (integer m/s)
        vmax_needed = int(math.ceil(V_LIST.max()))
        v_bins = list(range(0, vmax_needed + 1))
        slices = build_velocity_slices(profile, v_bins)

        # Prepare per-sample interpolation helpers
        bin_map = {}
        for vb in v_bins:
            interp = prep_bin_interps(slices.get(vb))
            if interp is not None:
                bin_map[vb] = interp

        if DEBUG:
            print("prop:", profile.name, "bins:", len(bin_map))

        for mname, motor in motors.items():
            # Skip motors with invalid kv
            if not math.isfinite(motor.kv) or motor.kv <= 0:
                continue

            # Motor constants
            kt = 60.0 / (TWO_PI * motor.kv)   # Nm/A (kv in rpm/V)
            inv_kt = 1.0 / kt
            R = float(motor.resistance)

            # Output file
            fname = f"{sanitize(profile.name)}__{sanitize(mname)}.txt"
            fpath = os.path.join(OUT_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                # NEW: write weight as first line
                weight = getattr(motor, "weight_g", float("nan"))
                f.write(f"weight_g,{float(weight):.6f}\n")

                # Existing header and data
                f.write("thrust_N,velocity_m_s,power_W\n")
                rows = []
                FLUSH_EVERY = 16384

                # Loop velocities; blend between neighboring samples
                for idx_v, v in enumerate(V_LIST):
                    v_lo = int(math.floor(v))
                    v_hi = int(math.ceil(v))
                    lo = bin_map.get(v_lo)
                    hi = bin_map.get(v_hi)

                    if v_hi != v_lo:
                        # Require both neighbors to blend
                        if lo is None or hi is None:
                            continue
                        a = (v - v_lo) / (v_hi - v_lo)

                        p_lo, rpm_lo, tq_lo = eval_bin_at_thrust(lo, T_LIST)
                        p_hi, rpm_hi, tq_hi = eval_bin_at_thrust(hi, T_LIST)
                        valid = np.isfinite(p_lo) & np.isfinite(p_hi)

                        if not np.any(valid):
                            continue

                        # Blend rpm/torque at this velocity
                        rpm_vec = (1 - a) * rpm_lo[valid] + a * rpm_hi[valid]
                        tq_vec  = (1 - a) * tq_lo[valid]  + a * tq_hi[valid]
                        t_ok    = T_LIST[valid]
                    else:
                        # Exact integer velocity: single sample
                        if lo is None:
                            continue
                        p_vec, rpm_vec, tq_vec = eval_bin_at_thrust(lo, T_LIST)
                        valid = np.isfinite(p_vec) & np.isfinite(rpm_vec) & np.isfinite(tq_vec)
                        if not np.any(valid):
                            continue
                        rpm_vec = rpm_vec[valid]
                        tq_vec  = tq_vec[valid]
                        t_ok    = T_LIST[valid]

                    # Electrical input power
                    omega = rpm_vec * OMEGA_SCALE
                    Iload = tq_vec * inv_kt
                    v_est = (omega * kt) + Iload * R
                    I0 = no_load_current(v_est, motor)
                    Itotal = Iload + I0
                    power_W = Itotal * v_est

                    # Buffer CSV lines
                    for t_val, p_val in zip(t_ok, power_W):
                        rows.append(f"{float(t_val):.6f},{float(v):.6f},{float(p_val):.6f}\n")

                    # Flush and progress
                    if len(rows) >= FLUSH_EVERY:
                        f.writelines(rows)
                        rows.clear()
                    if DEBUG and ((idx_v + 1) % PROGRESS_EVERY_VELOCITIES == 0):
                        print("progress", profile.name, mname, "v_idx", idx_v + 1, "/", len(V_LIST))

                if rows:
                    f.writelines(rows)

            if DEBUG:
                print("done", profile.name, mname)


if __name__ == "__main__":
    main()
