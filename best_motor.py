import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# add local import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aero_utils.motor_parser import load_motor_models
from aero_utils.propdata_interp import get_prop_data

# config
propeller_name = "27x13E"
airspeed = 20          # m/s
thrust = 173.481            # N
cell_count = 13        # LiPo cells
esc_efficiency = 0.97
battery_voltage_limit = cell_count * 4.2  # V
SELECTION_MODE ="lenient"  # "strict" or "lenient"

motors = load_motor_models()

labels = []
efficiencies = []
currents = []
voltages = []
input_powers = []
output_powers = []
current_statuses = []
voltage_statuses = []
rpm_statuses = []
current_limits = []
voltage_maxes = []
rpm_limits = []
skipped_motors = []

reasons = {"prop_none": 0, "over_battery": 0, "exception": 0}
examples = {"prop_none": None, "over_battery": None, "exception": None}

prop = get_prop_data(propeller_name, airspeed, thrust)
if prop is None:
    reasons["prop_none"] = len(motors)
    examples["prop_none"] = (propeller_name, airspeed, thrust)
    print(f"\nNo prop solution for {propeller_name} at {airspeed} m/s and {thrust} N.")
    print("All motors will be skipped (reason: prop_none).")
    print(f"Evaluated {len(motors)} motors. Kept 0; Skipped {len(motors)}.")
    print("Skip reasons:", reasons)
    sys.exit(0)

for name, motor in motors.items():
    try:
        omega = (prop['rpm'] / 60.0) * 2.0 * np.pi
        kt = 60.0 / (2.0 * np.pi * motor.kv)   # N*m/A (Kv in rpm/V)
        Iload = prop['torque'] / kt
        a = motor.no_load_current_AperV        # A/V
        denom = 1.0 - a * motor.resistance
        if abs(denom) < 1e-9:
            raise ValueError("Ill-conditioned: 1 - (no_load_current_AperV * resistance) ~ 0")

        v_est = (omega * kt + Iload * motor.resistance) / denom
        I0 = a * v_est
        Itotal = Iload + I0

        if v_est > battery_voltage_limit:
            reasons["over_battery"] += 1
            if examples["over_battery"] is None:
                examples["over_battery"] = (name, v_est, Itotal)
            skipped_motors.append(name)
            continue

        Pin = Itotal * v_est
        Pout = prop['torque'] * omega
        esc_loss = Pin * (1.0 / esc_efficiency - 1.0)
        total_input = Pin + esc_loss
        eff = Pout / total_input if total_input > 0 else 0.0

        current_margin = motor.current_limit * 0.85
        voltage_margin = motor.voltage_max * 0.85
        current_status = 'fail' if Itotal > motor.current_limit else 'margin' if Itotal > current_margin else 'pass'
        voltage_status = 'fail' if v_est > motor.voltage_max else 'margin' if v_est > voltage_margin else 'pass'

        rlim = getattr(motor, "rpm_limit", float("inf"))
        rpm_limits.append(rlim if np.isfinite(rlim) else None)
        if np.isfinite(rlim):
            rmargin = 0.85 * rlim
            rpm_status = 'fail' if prop['rpm'] > rlim else 'margin' if prop['rpm'] > rmargin else 'pass'
        else:
            rpm_status = 'pass'

        labels.append(name)
        efficiencies.append(eff * 100.0)
        currents.append(Itotal)
        voltages.append(v_est)
        input_powers.append(Pin)
        output_powers.append(Pout)
        current_statuses.append(current_status)
        voltage_statuses.append(voltage_status)
        rpm_statuses.append(rpm_status)
        current_limits.append(motor.current_limit)
        voltage_maxes.append(motor.voltage_max)

    except Exception as e:
        reasons["exception"] += 1
        if examples["exception"] is None:
            examples["exception"] = (name, type(e).__name__, str(e))
        skipped_motors.append(name)
        continue

print(f"\nEvaluated {len(motors)} motors.")
print(f"Kept {len(labels)}; Skipped {len(skipped_motors)}.")
print("Skip reasons:", reasons)
if examples["over_battery"]:
    n, v, I = examples["over_battery"]
    print(f"Example over-battery: {n} -> V_est={v:.2f} V, I_total={I:.1f} A (battery limit={battery_voltage_limit:.1f} V)")
if examples["exception"]:
    n, et, msg = examples["exception"]
    print(f"Example exception: {n} -> {et}: {msg}")

if len(labels) == 0:
    print("\nNo motors kept. Exiting.")
    sys.exit(0)

# build records
records = []
for i, name in enumerate(labels):
    total_in = input_powers[i] / esc_efficiency  # battery-side power
    rec = {
        "name": name,
        "eff_pct": efficiencies[i],
        "I_total_A": currents[i],
        "V_motor_V": voltages[i],
        "Pin_W": input_powers[i],
        "Pout_W": output_powers[i],
        "TotalIn_W": total_in,
        "current_status": current_statuses[i],
        "voltage_status": voltage_statuses[i],
        "rpm_status": rpm_statuses[i],
        "I_limit_A": current_limits[i],
        "V_max_V": voltage_maxes[i],
        "rpm": prop["rpm"],
        "torque_Nm": prop["torque"],
        "current_ratio": currents[i] / current_limits[i] if current_limits[i] > 0 else np.inf,
        "voltage_ratio": voltages[i] / voltage_maxes[i] if voltage_maxes[i] > 0 else np.inf,
        "rpm_ratio": (prop["rpm"] / rpm_limits[i]) if rpm_limits[i] not in (None, 0) else 0.0,
    }
    records.append(rec)

def passes_mode(rec, mode="strict"):
    ok_c = (rec["current_status"] == "pass") if mode == "strict" else (rec["current_status"] in ("pass", "margin"))
    ok_v = (rec["voltage_status"] == "pass") if mode == "strict" else (rec["voltage_status"] in ("pass", "margin"))
    ok_r = (rec["rpm_status"] == "pass") if mode == "strict" else (rec["rpm_status"] in ("pass", "margin"))
    return ok_c and ok_v and ok_r

# choose candidates according to configured mode
mode_used = SELECTION_MODE
candidates = [r for r in records if passes_mode(r, SELECTION_MODE)]
if not candidates and SELECTION_MODE == "strict":
    candidates = [r for r in records if passes_mode(r, "lenient")]
    mode_used = "lenient (fallback)"

if not candidates:
    print(f"\nNo viable candidates under {SELECTION_MODE}.")
else:
    candidates.sort(key=lambda r: (r["TotalIn_W"], -r["eff_pct"], r["I_total_A"]))
    best = candidates[0]

    print(f"\nBest motor ({mode_used})")
    print(f"Name: {best['name']}")
    print(f"Total input (battery): {best['TotalIn_W']:.1f} W")
    print(f"Shaft power: {best['Pout_W']:.1f} W")
    print(f"System efficiency: {best['eff_pct']:.2f} %")
    print(f"Motor V/I: {best['V_motor_V']:.2f} V, {best['I_total_A']:.1f} A")
    print(f"Statuses I/V/RPM: {best['current_status']} / {best['voltage_status']} / {best['rpm_status']}")
    print(f"Headroom I: {100*(1 - best['current_ratio']):.1f}% of limit")
    print(f"Headroom V: {100*(1 - best['voltage_ratio']):.1f}% of V_max (battery limit {battery_voltage_limit:.1f} V)")
    if best['rpm_ratio'] > 0:
        print(f"Headroom RPM: {100*(1 - best['rpm_ratio']):.1f}% of rpm_limit")

    # cross-motor plot by total battery input power
    names = [r["name"] for r in candidates]
    tot_in = np.array([r["TotalIn_W"] for r in candidates])
    order = np.argsort(tot_in)
    names_sorted = [names[i] for i in order]
    tot_in_sorted = tot_in[order]

    plt.figure()
    plt.bar(names_sorted, tot_in_sorted)
    plt.ylabel("total input power (W)")
    plt.title(f"battery power at {airspeed} m/s, {thrust} N (prop: {propeller_name}, mode: {mode_used})")
    plt.xticks(rotation=60, ha='right')
    plt.tight_layout()

    # power breakdown for the best motor
    m = motors[best["name"]]
    omega = (prop['rpm'] / 60.0) * 2.0 * np.pi
    kt = 60.0 / (2.0 * np.pi * m.kv)
    Iload = prop['torque'] / kt
    a = m.no_load_current_AperV
    v_est = (omega * kt + Iload * m.resistance) / (1.0 - a * m.resistance)
    I0 = a * v_est
    Itotal = Iload + I0
    Pin = Itotal * v_est
    Pout = prop['torque'] * omega
    esc_loss = Pin * (1.0 / esc_efficiency - 1.0)
    Pcopper = (Iload ** 2) * m.resistance
    Pno_load = I0 * v_est
    residual = max(0.0, Pin - Pcopper - Pno_load - Pout)
    battery_total = Pin + esc_loss

    parts = [esc_loss, Pcopper, Pno_load, Pout, residual]
    labels_parts = ["ESC loss", "Copper loss", "No-load loss", "Shaft power", "Other"]

    plt.figure()
    bottom = 0.0
    for p, lab in zip(parts, labels_parts):
        plt.bar([best["name"]], [p], bottom=[bottom], label=lab)
        bottom += p
    plt.ylabel("power (W)")
    plt.title(f"{best['name']}: power breakdown at {airspeed} m/s, {thrust} N (total ≈ {battery_total:.0f} W)")
    plt.legend()
    plt.tight_layout()

    plt.show()

# if there were no candidates at all, still consider showing the kept set for debugging
if not candidates and len(records) > 0:
    names = [r["name"] for r in records]
    tot_in = np.array([r["TotalIn_W"] for r in records])
    order = np.argsort(tot_in)
    names_sorted = [names[i] for i in order]
    tot_in_sorted = tot_in[order]

    plt.figure()
    plt.bar(names_sorted, tot_in_sorted)
    plt.ylabel("total input power (W)")
    plt.title(f"battery power (all kept) at {airspeed} m/s, {thrust} N (prop: {propeller_name})")
    plt.xticks(rotation=60, ha='right')
    plt.tight_layout()
    plt.show()
