import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# add local import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aero_utils.motor_parser import load_motor_models
from aero_utils.propdata_interp import get_prop_data

# config
propeller_name = "18x12E"
airspeed = 28                        # m/s
thrust = 28                          # N
cell_count = 6                      # LiPo cells
esc_efficiency = 0.97
battery_voltage_limit = cell_count * 4.2  # V

# map status codes to bar colors
def get_colors(status_list):
    return ['green' if s == 'pass' else 'orange' if s == 'margin' else 'red' for s in status_list]

# main
motors = load_motor_models()

labels = []
efficiencies = []
currents = []
voltages = []
input_powers = []
output_powers = []
current_statuses = []
voltage_statuses = []
skipped_motors = []

print

for name, motor in motors.items():
    try:
        prop = get_prop_data(propeller_name, airspeed, thrust)
        if prop is None:
            skipped_motors.append(name)
            continue

        # motor model
        omega = (prop['rpm'] / 60) * 2 * np.pi
        kt = 60 / (2 * np.pi * motor.kv)
        Iload = prop['torque'] / kt
        backEMF = omega * kt
        v_est = backEMF + Iload * motor.resistance
        I0 = motor.no_load_current_AperV * v_est
        Itotal = Iload + I0

        if v_est > battery_voltage_limit:
            skipped_motors.append(name)
            continue

        # power and efficiency
        Pin = Itotal * v_est
        Pout = prop['torque'] * omega
        esc_loss = Pin * (1 / esc_efficiency - 1)
        total_input = Pin + esc_loss
        eff = Pout / total_input

        # limit checks
        current_margin = motor.current_limit * 0.85
        voltage_margin = motor.voltage_max * 0.85

        current_status = (
            'fail' if Itotal > motor.current_limit else
            'margin' if Itotal > current_margin else
            'pass'
        )

        voltage_status = (
            'fail' if v_est > motor.voltage_max else
            'margin' if v_est > voltage_margin else
            'pass'
        )

        # store results
        labels.append(name)
        efficiencies.append(eff * 100)
        currents.append(Itotal)
        voltages.append(v_est)
        input_powers.append(Pin)
        output_powers.append(Pout)
        current_statuses.append(current_status)
        voltage_statuses.append(voltage_status)

    except Exception:
        skipped_motors.append(name)
        continue

# print skipped motors
if skipped_motors:
    print("\nskipped motors due to missing prop data or voltage overlimit:")
    for m in skipped_motors:
        print(f" - {m}")
else:
    print("\nall motors evaluated successfully.")

# plots

# efficiency
plt.figure()
plt.bar(labels, efficiencies, color='skyblue')
plt.ylabel("efficiency (%)")
plt.title(f"efficiency at {airspeed} m/s, {thrust} N\npropeller: {propeller_name}")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# current
plt.figure()
plt.bar(labels, currents, color=get_colors(current_statuses))
plt.ylabel("total current (A)")
plt.title(f"current draw at {airspeed} m/s, {thrust} N\npropeller: {propeller_name}")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# voltage
plt.figure()
plt.bar(labels, voltages, color=get_colors(voltage_statuses))
plt.axhline(battery_voltage_limit, color='black', linestyle='--', label="battery limit")
plt.ylabel("motor voltage (V)")
plt.title(f"voltage at {airspeed} m/s, {thrust} N\nbattery: {cell_count}S")
plt.xticks(rotation=45, ha='right')
plt.legend()
plt.tight_layout()

# power
x = np.arange(len(labels))
bar_width = 0.35

plt.figure()
plt.bar(x - 0.2, input_powers, width=bar_width, label="input power", color='gray')
plt.bar(x + 0.2, output_powers, width=bar_width, label="output power", color='lightgreen')
plt.xticks(x, labels, rotation=45, ha='right')
plt.ylabel("power (W)")
plt.title(f"power comparison at {airspeed} m/s, {thrust} N")
plt.legend()
plt.tight_layout()

plt.show()
