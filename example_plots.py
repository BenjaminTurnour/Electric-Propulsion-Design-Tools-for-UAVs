import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add current directory to path so local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import loaders and utilities
from aero_utils.xfoil_parser import load_all_polars
from aero_utils.propdata_parser import load_all_propellers
from aero_utils.motor_parser import load_all_motor_models
from aero_utils.propdata_interp import build_velocity_slices

# Load airfoils
print("Loading airfoils...")
airfoils = load_all_polars("polars")
print(f"Loaded {len(airfoils)} airfoils.")

# Load motors
print("Loading motors...")
motors = load_all_motor_models("motors")
print(f"Loaded {len(motors)} motors.")

# Load one propeller
print("Loading one propeller...")
propellers = load_all_propellers("APC")
if not propellers:
    print("No propeller files found.")
    sys.exit()

profile = propellers[300]
print(f"Using propeller: {profile.name}")

# Plot airfoil drag polars
plt.figure()
for foil in airfoils:
    plt.plot(foil.cd, foil.cl, label=foil.name)
plt.xlabel("Cd")
plt.ylabel("Cl")
plt.title("Airfoil Drag Polars")
plt.grid(True)
plt.legend()

# Build velocity slices for the propeller
slices = build_velocity_slices(profile, list(range(0, 72, 2)))
velocities = sorted(slices.keys())
power_percentages = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

rpm_lines = {}
torque_lines = {}
thrust_lines = {}

for percent in power_percentages:
    rpm_lines[percent] = []
    torque_lines[percent] = []
    thrust_lines[percent] = []

    for v in velocities:
        interp = slices[v]
        pmin, pmax = interp['power_range']
        target_power = percent * pmax

        if pmin <= target_power <= pmax:
            rpm = interp['interp_rpm'](target_power)
            torque = interp['interp_torque'](target_power)
            thrust = interp['interp_thrust'](target_power)

            rpm_lines[percent].append((v, rpm))
            torque_lines[percent].append((v, torque))
            thrust_lines[percent].append((v, thrust))

# Use separate colormaps for each plot
cmap_rpm = plt.cm.plasma
cmap_torque = plt.cm.viridis
cmap_thrust = plt.cm.inferno

colors_rpm = cmap_rpm(np.linspace(0, 1, len(power_percentages)))
colors_torque = cmap_torque(np.linspace(0, 1, len(power_percentages)))
colors_thrust = cmap_thrust(np.linspace(0, 1, len(power_percentages)))

# Plot RPM vs Velocity
plt.figure()
for i, (percent, points) in enumerate(rpm_lines.items()):
    if points:
        v_vals, y_vals = zip(*points)
        plt.plot(v_vals, y_vals, color=colors_rpm[i], label=f"{int(percent * 100)}% Power")
plt.title(f"{profile.name} - RPM vs Velocity")
plt.xlabel("Velocity (m/s)")
plt.ylabel("RPM")
plt.grid(True)
plt.legend()

# Plot Torque vs Velocity
plt.figure()
for i, (percent, points) in enumerate(torque_lines.items()):
    if points:
        v_vals, y_vals = zip(*points)
        plt.plot(v_vals, y_vals, color=colors_torque[i], label=f"{int(percent * 100)}% Power")
plt.title(f"{profile.name} - Torque vs Velocity")
plt.xlabel("Velocity (m/s)")
plt.ylabel("Torque (Nm)")
plt.grid(True)
plt.legend()

# Plot Thrust vs Velocity
plt.figure()
for i, (percent, points) in enumerate(thrust_lines.items()):
    if points:
        v_vals, y_vals = zip(*points)
        plt.plot(v_vals, y_vals, color=colors_thrust[i], label=f"{int(percent * 100)}% Power")
plt.title(f"{profile.name} - Thrust vs Velocity")
plt.xlabel("Velocity (m/s)")
plt.ylabel("Thrust (N)")
plt.grid(True)
plt.legend()

# Show all plots
plt.show()
