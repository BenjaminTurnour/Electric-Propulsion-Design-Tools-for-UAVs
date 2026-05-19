# -----------------------------------------------------------------------------
# SUMMARY:
# This script performs a "Best Match Index" (BMI) analysis across all APC propellers.
# For a grid of thrust and velocity targets, it:
#   1. Loads and interpolates performance data for each propeller.
#   2. Determines which propeller(s) can produce the desired thrust at each velocity.
#   3. Finds the 1st, 2nd, and 3rd most power-efficient propellers for each (velocity, thrust) pair.
#   4. Saves the results as labeled CSV files for later inspection or visualization.
# -----------------------------------------------------------------------------

import numpy as np
import pandas as pd

from aero_utils.propdata_parser import load_all_propellers
from aero_utils.propdata_interp import build_velocity_slices

# Load all APC propeller data from the "APC" folder
propellers = load_all_propellers("APC")

# You can exclude certain propellers from consideration
exclude_props = [

]

# Define the airspeed and power grids to use for interpolation
v_grid = np.linspace(0, 180, 500)   # airspeed from 0 to 180 m/s
p_grid = np.linspace(0, 5000, 51)  # power from 0 to 5000 W
VV, PP = np.meshgrid(v_grid, p_grid)

# Store full interpolated data for each propeller
propeller_data = {}
all_thrust_values = []  # Used to find the overall thrust range

# Loop over all loaded propellers
for profile in propellers:
    # Interpolate performance across all target velocities
    slices = build_velocity_slices(profile, v_grid)

    # Prepare 2D arrays to store interpolated RPM, torque, and thrust
    rpm_arr = np.full_like(VV, np.nan)
    torque_arr = np.full_like(VV, np.nan)
    thrust_arr = np.full_like(VV, np.nan)

    print(f"\n=== {profile.name} ===")
    for i in range(VV.shape[0]):
        for j in range(VV.shape[1]):
            v = VV[i, j]
            p = PP[i, j]

            # Only interpolate if we have data for this velocity
            if v in slices:
                data = slices[v]
                pw = data['power_w']
                if min(pw) <= p <= max(pw):
                    rpm = np.interp(p, pw, data['rpm'])
                    torque = np.interp(p, pw, data['torque'])
                    thrust = np.interp(p, pw, data['thrust'])

                    rpm_arr[i, j] = rpm
                    torque_arr[i, j] = torque
                    thrust_arr[i, j] = thrust
                    all_thrust_values.append(thrust)

    # Print thrust ranges at each velocity for diagnostics
    for v in slices:
        t_vals = slices[v]['thrust']
        if len(t_vals) > 0:
            print(f"v = {v:.1f} m/s thrust range: {min(t_vals):.2f} to {max(t_vals):.2f} N")

    # Save all interpolated data for later lookup
    propeller_data[profile.name] = {
        "velocity": VV,
        "power": PP,
        "rpm": rpm_arr,
        "torque": torque_arr,
        "thrust": thrust_arr
    }

print("\nFinished interpolating all propellers.")

# Create a grid of thrust targets for each airspeed, in descending thrust order
max_thrust_overall = np.nanmax(all_thrust_values)
bmi_t = np.round(np.linspace(0, max_thrust_overall, 500), 3)[::-1]  # 500 thrust levels
bmi_v = v_grid.copy()  # Use same airspeed grid
VV_bmi, TT_bmi = np.meshgrid(bmi_v, bmi_t)
print("\ncreated grid")
# Grids to store minimum, second, and third best power results
min_power_grid     = np.full_like(VV_bmi, np.nan, dtype=float)
second_power_grid  = np.full_like(VV_bmi, np.nan, dtype=float)
third_power_grid   = np.full_like(VV_bmi, np.nan, dtype=float)
print("created power grids")
# Grids to store corresponding propeller names
best_prop_grid     = np.full(VV_bmi.shape, "", dtype=object)
second_prop_grid   = np.full(VV_bmi.shape, "", dtype=object)
third_prop_grid    = np.full(VV_bmi.shape, "", dtype=object)
print("created propeller grids")
# For each (velocity, thrust) target...
for i in range(VV_bmi.shape[0]):
    for j in range(VV_bmi.shape[1]):
        v_target = VV_bmi[i, j]
        t_target = TT_bmi[i, j]

        candidates = []  # Store (power_required, propeller_name)
        print("Evaluating BMI for v = {:.1f} m/s, T = {:.2f} N".format(v_target, t_target))
        for name, data in propeller_data.items():
            if name in exclude_props:
                continue

            # Find the velocity column that matches v_target
            v_column = data["velocity"][0, :]
            idx_v = np.where(np.isclose(v_column, v_target, atol=1e-6))[0]
            if len(idx_v) == 0:
                continue
            v_idx = idx_v[0]

            thrust_col = data["thrust"][:, v_idx]
            power_col = data["power"][:, v_idx]

            if np.all(np.isnan(thrust_col)):
                continue

            # Only consider if this propeller can generate the target thrust
            t_min, t_max = np.nanmin(thrust_col), np.nanmax(thrust_col)
            if t_min <= t_target <= t_max:
                power_required = np.interp(t_target, thrust_col, power_col)
                candidates.append((power_required, name))

        # Sort all viable candidates by lowest power requirement
        if candidates:
            candidates.sort()
            if len(candidates) > 0:
                min_power_grid[i, j] = candidates[0][0]
                best_prop_grid[i, j] = candidates[0][1]
            if len(candidates) > 1:
                second_power_grid[i, j] = candidates[1][0]
                second_prop_grid[i, j] = candidates[1][1]
            if len(candidates) > 2:
                third_power_grid[i, j] = candidates[2][0]
                third_prop_grid[i, j] = candidates[2][1]
print("\nCompleted BMI analysis for all (velocity, thrust) pairs.")
# Convert results into labeled DataFrames
power_df = pd.DataFrame(min_power_grid, index=bmi_t, columns=bmi_v)
prop_df = pd.DataFrame(best_prop_grid, index=bmi_t, columns=bmi_v)
print("\nConverted results to DataFrames.")
# Add a label column for thrust (row header)
power_df.insert(0, "Thrust (N)", power_df.index)
prop_df.insert(0, "Thrust (N)", prop_df.index)
print("Added thrust labels to DataFrames.")
# Rename column headers to include units (e.g., "20.0 m/s")
power_df.columns = ["Thrust (N)"] + [f"{v} m/s" for v in bmi_v]
prop_df.columns = ["Thrust (N)"] + [f"{v} m/s" for v in bmi_v]
print("Renamed column headers to include velocity units.")
# Add one row at the bottom with the velocity labels for extra clarity
power_label_row = ["Velocity (m/s)"] + [f"{v}" for v in bmi_v]
prop_label_row = ["Velocity (m/s)"] + [f"{v}" for v in bmi_v]
power_df = pd.concat([power_df, pd.DataFrame([power_label_row], columns=power_df.columns)], ignore_index=True)
prop_df = pd.concat([prop_df, pd.DataFrame([prop_label_row], columns=prop_df.columns)], ignore_index=True)
print("Added velocity label row at the bottom of DataFrames.")
# Save the DataFrames to CSV
power_df.to_csv("bmi_power_values_labeled.csv", index=False)
prop_df.to_csv("bmi_best_propeller_labeled.csv", index=False)

print("\n BMI analysis complete with labeled axes.")
print("  - Saved to 'bmi_power_values_labeled.csv'")
print("  - Saved to 'bmi_best_propeller_labeled.csv'")

# Helper function for exporting other labeled DataFrames
def export_labeled_grid(data, row_labels, col_labels, filename, row_title="Thrust (N)", col_title="Velocity (m/s)"):
    df = pd.DataFrame(data, index=row_labels, columns=col_labels)
    df.insert(0, row_title, df.index)
    df.columns = [row_title] + [f"{v} m/s" for v in col_labels]
    label_row = [col_title] + [f"{v}" for v in col_labels]
    df = pd.concat([df, pd.DataFrame([label_row], columns=df.columns)], ignore_index=True)
    df.to_csv(filename, index=False)
    print(f"  - Saved to '{filename}'")

# Save second-best and third-best result tables
export_labeled_grid(second_power_grid, bmi_t, bmi_v, "bmi_second_best_power_labeled.csv")
export_labeled_grid(second_prop_grid, bmi_t, bmi_v, "bmi_second_best_propeller_labeled.csv")
export_labeled_grid(third_power_grid, bmi_t, bmi_v, "bmi_third_best_power_labeled.csv")
export_labeled_grid(third_prop_grid, bmi_t, bmi_v, "bmi_third_best_propeller_labeled.csv")
