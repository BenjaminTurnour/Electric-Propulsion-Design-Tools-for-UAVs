# -------------------------------------------------------------
# SUMMARY:
# This script visualizes the performance of a selected APC propeller.
# It performs the following steps:
# 1. Loads all APC propeller data files.
# 2. Prompts the user to enter a propeller size (e.g., "10x5").
# 3. Interpolates thrust, torque, and RPM data across velocities and power levels.
# 4. Plots:
#    - RPM, torque, and thrust vs airspeed at selected power levels.
#    - Contour plots showing how RPM, torque, and thrust vary with airspeed and power input.
# -------------------------------------------------------------

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add the current directory to the Python path to allow local imports to work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions that load and interpolate propeller data
from aero_utils.propdata_parser import load_all_propellers
from aero_utils.propdata_interp import build_velocity_slices

# Load all APC propeller profiles from the "APC" folder
propellers = load_all_propellers("APC")

# Ask the user for a specific propeller size
# e.g., if the user types "10x5", the script looks for a file named "PER3_10x5"
desired_file = "PER3_" + input("propeller dimensions: ")

# Check if the file exists in the loaded propeller profiles
if desired_file in [p.name for p in propellers]:
    # Keep only the matching propeller
    propellers = [p for p in propellers if p.name == desired_file]
else:
    # Raise an error if the propeller file is not found
    raise ValueError(f"Propeller file '{desired_file}' not found.")

# Loop over each matching propeller (should just be one)
for profile in propellers:
    # Build slices of performance data over a range of velocities from 0 to 179 mph
    slices = build_velocity_slices(profile, list(range(0, 180, 1)))
    velocities = sorted(slices.keys())

    # If no data is available, skip this profile
    if not velocities:
        continue

    # Find all power values available for each velocity slice
    all_powers = [slices[v]['power_w'] for v in velocities if 'power_w' in slices[v]]

    # Find power values common to all velocities (intersection of power lists)
    common_power_range = list(set.intersection(*[set(map(int, pw)) for pw in all_powers]))
    common_power_range = sorted(common_power_range)

    if not common_power_range:
        raise RuntimeError("No common power values across velocities.")

    # Select 6 evenly spaced power values for plotting
    selected_power_values = [common_power_range[int(i)] for i in np.linspace(0, len(common_power_range)-1, 6).astype(int)]
    power_labels = [f"{int(p)} W" for p in selected_power_values]

    # Prepare lists to store performance curves
    rpm_lines = []
    torque_lines = []
    thrust_lines = []

    # Interpolate performance (RPM, torque, thrust) vs airspeed for each selected power level
    for p in selected_power_values:
        rpm_line = []
        torque_line = []
        thrust_line = []

        for v in velocities:
            data = slices[v]
            pw = data['power_w']
            # Only interpolate if the desired power is within the available range
            if min(pw) <= p <= max(pw):
                rpm = np.interp(p, data['power_w'], data['rpm'])
                torque = np.interp(p, data['power_w'], data['torque'])
                thrust = np.interp(p, data['power_w'], data['thrust'])

                rpm_line.append((v, rpm))
                torque_line.append((v, torque))
                thrust_line.append((v, thrust))

        rpm_lines.append(rpm_line)
        torque_lines.append(torque_line)
        thrust_lines.append(thrust_line)

    # Assign distinct colors for each power level for plotting
    cmap_rpm = plt.cm.tab10
    cmap_torque = plt.cm.viridis
    cmap_thrust = plt.cm.inferno

    colors_rpm = cmap_rpm(np.linspace(0, 1, len(selected_power_values)))
    colors_torque = cmap_torque(np.linspace(0, 1, len(selected_power_values)))
    colors_thrust = cmap_thrust(np.linspace(0, 1, len(selected_power_values)))

    # Create 2D grids for contour plots: airspeed (0–180 mph) vs power (0–5000 W)
    v_grid = np.linspace(0, 180, 91)     # horizontal axis: airspeed
    p_grid = np.linspace(0, 5000, 51)    # vertical axis: power

    VV, PP = np.meshgrid(v_grid, p_grid)
    Torque = np.full_like(VV, np.nan)    # initialize torque values

    # Fill in the Torque array by interpolating from slices
    for i in range(VV.shape[0]):
        for j in range(VV.shape[1]):
            v = VV[i, j]
            p = PP[i, j]
            if v in slices:
                data = slices[v]
                pw = data['power_w']
                if min(pw) <= p <= max(pw):
                    torque = np.interp(p, pw, data['torque'])
                    Torque[i, j] = torque

    # Plot torque contour plot
    CS = plt.contour(VV, PP, Torque, cmap='Reds')
    plt.clabel(CS, inline=True, fontsize=10)
    plt.xlabel("Velocity (mph)")
    plt.ylabel("Power (W)")
    plt.title("Torque (Nm)")
    plt.grid(True)

    # Automatically adjust axis limits to only show valid data
    valid_mask = ~np.isnan(Torque)
    v_max = np.max(VV[valid_mask])
    p_max = np.max(PP[valid_mask])
    v_min = np.min(VV[valid_mask])
    p_min = np.min(PP[valid_mask])
    plt.xlim(v_min, v_max)
    plt.ylim(p_min, p_max)

    # ---- Plot RPM Contour ----
    RPM = np.full_like(VV, np.nan)
    for i in range(VV.shape[0]):
        for j in range(VV.shape[1]):
            v = VV[i, j]
            p = PP[i, j]
            if v in slices:
                data = slices[v]
                pw = data['power_w']
                if min(pw) <= p <= max(pw):
                    rpm = np.interp(p, pw, data['rpm'])
                    RPM[i, j] = rpm

    # Start a new figure for RPM and thrust
    plt.figure()
    CS = plt.contour(VV, PP, RPM, cmap='Blues')
    plt.clabel(CS, inline=True, fontsize=10)
    plt.xlabel("Velocity (mph)")
    plt.ylabel("Power (W)")
    plt.title("Blue: RPM     Green: Thrust")
    plt.grid(True)

    # ---- Plot Thrust Contour ----
    Thrust = np.full_like(VV, np.nan)
    for i in range(VV.shape[0]):
        for j in range(VV.shape[1]):
            v = VV[i, j]
            p = PP[i, j]
            if v in slices:
                data = slices[v]
                pw = data['power_w']
                if min(pw) <= p <= max(pw):
                    thrust = np.interp(p, pw, data['thrust'])
                    Thrust[i, j] = thrust

    # Overlay thrust contours on the same figure
    CS = plt.contour(VV, PP, Thrust, cmap='Greens')
    plt.clabel(CS, inline=True, fontsize=10)

    # Adjust axis limits again based on valid RPM data
    valid_mask_R = ~np.isnan(RPM)
    v_max = np.max(VV[valid_mask_R])
    p_max = np.max(PP[valid_mask_R])
    v_min = np.min(VV[valid_mask_R])
    p_min = np.min(PP[valid_mask_R])
    plt.xlim(v_min, v_max)
    plt.ylim(p_min, p_max)

# Show all generated plots
plt.show()
