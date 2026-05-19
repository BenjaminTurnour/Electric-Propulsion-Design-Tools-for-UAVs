# ---------------------------------------------------------------------------
# SUMMARY:
# This module defines a function to generate performance data for a propeller
# at a range of airspeeds and power inputs using interpolation and root solving.
#
# Function:
#   build_velocity_slices(profile, velocity_targets)
#
# INPUT:
#   - profile: A PropellerProfile object containing data blocks at various RPMs.
#   - velocity_targets: A list of airspeeds (in m/s) to evaluate.
#
# WHAT IT DOES:
#   For each target airspeed, this function:
#     1. Interpolates torque and thrust values across all available RPM blocks.
#     2. Solves for the RPM that would result in specific power values.
#     3. Returns thrust, torque, RPM, and power values for each airspeed.
#
# OUTPUT:
#   - A dictionary mapping each airspeed to interpolated lists of:
#     power_w, rpm, torque, and thrust.
# ---------------------------------------------------------------------------

import numpy as np
from typing import List, Dict
from scipy.optimize import root_scalar

from aero_utils.propdata_parser import PropellerProfile
from aero_utils.propdata_parser import load_all_propellers

# This function creates interpolated performance data across velocities
def build_velocity_slices(profile: PropellerProfile, velocity_targets: List[float]) -> Dict[float, Dict[str, List[float]]]:
    velocity_map = {}  # Dictionary to hold results for each velocity

    # Define a range of power inputs to solve for (in watts)
    # You can change the range or number of points if needed
    power_targets = np.linspace(500, 5000, 20)

    # Loop through each desired airspeed
    for v_target in velocity_targets:
        rpm_list = []
        torque_list = []
        thrust_list = []

        # Loop through each data block (which represents a specific RPM)
        for block in profile.blocks:
            # Check if this block contains data that spans the target velocity
            if np.min(block.v) <= v_target <= np.max(block.v):
                try:
                    # Interpolate torque and thrust at this velocity within the block
                    torque_v = float(np.interp(v_target, block.v, block.torque_nm))
                    thrust_v = float(np.interp(v_target, block.v, block.thrust_n))

                    # Store the interpolated values and their corresponding RPM
                    rpm_list.append(block.rpm)
                    torque_list.append(torque_v)
                    thrust_list.append(thrust_v)
                except:
                    # If interpolation fails, skip this block
                    continue

        # If we didn’t find any usable blocks, skip this velocity
        if len(rpm_list) < 2:
            continue  # Not enough points to interpolate over RPM

        # Sort data by RPM so interpolation works properly
        sorted_indices = np.argsort(rpm_list)
        rpm_array = np.array(rpm_list)[sorted_indices]
        torque_array = np.array(torque_list)[sorted_indices]
        thrust_array = np.array(thrust_list)[sorted_indices]

        # Prepare output lists for this velocity
        powers = []
        rpms = []
        torques = []
        thrusts = []

        # Loop through each desired power input and find the corresponding RPM
        for p in power_targets:
            # Define the function whose root we want to find: power = torque × angular velocity
            def residual(rpm):
                torque_guess = np.interp(rpm, rpm_array, torque_array)
                power_guess = torque_guess * (2 * np.pi * rpm / 60.0)  # Power = torque × ω
                return power_guess - p  # We want this to be zero

            try:
                # Solve for RPM such that power = p, using Brent's method
                result = root_scalar(residual, bracket=(rpm_array[0], rpm_array[-1]), method='brentq')

                if result.converged:
                    rpm_sol = result.root  # The RPM that solves the equation

                    # Interpolate corresponding torque and thrust at this RPM
                    torque_sol = float(np.interp(rpm_sol, rpm_array, torque_array))
                    thrust_sol = float(np.interp(rpm_sol, rpm_array, thrust_array))

                    # Save results
                    powers.append(p)
                    rpms.append(rpm_sol)
                    torques.append(torque_sol)
                    thrusts.append(thrust_sol)
            except Exception:
                # If root finding fails, skip this power level
                continue

        # Save all computed values for this velocity if we found any
        if powers:
            velocity_map[v_target] = {
                'power_w': powers,
                'rpm': rpms,
                'torque': torques,
                'thrust': thrusts
            }
    # Return the full map of velocity slices
    return velocity_map

def get_prop_data(prop_name: str, velocity: float, thrust: float):
    """
    Given a propeller name (e.g. '10x5'), a velocity (mph), and a desired thrust (N),
    returns the estimated RPM, torque (Nm), and power input (W) needed to produce that thrust.
    """
    # Load all propellers and find the requested one
    full_name = f"PER3_{prop_name}"
    all_props = load_all_propellers("APC")
    match = [p for p in all_props if p.name == full_name]
    if not match:
        raise ValueError(f"Propeller '{full_name}' not found in APC/ folder.")
    
    profile = match[0]

    # Build interpolated slices for airspeed
    slices = build_velocity_slices(profile, [int(round(velocity))])
    v_int = int(round(velocity))

    #if v_int not in slices:
    #    raise ValueError(f"No data available at {velocity} mph.")

    data = slices[v_int]

    # Ensure thrust is within range
    min_thrust = min(data["thrust"])
    max_thrust = max(data["thrust"])
    #if not (min_thrust <= thrust <= max_thrust):
    #    raise ValueError(f"Requested thrust {thrust} N is outside range [{min_thrust}, {max_thrust}]")

    # Interpolate to get required power for desired thrust
    power = np.interp(thrust, data["thrust"], data["power_w"])

    # Interpolate corresponding RPM and torque
    rpm = np.interp(power, data["power_w"], data["rpm"])
    torque = np.interp(power, data["power_w"], data["torque"])

    return {
        "rpm": rpm,
        "torque": torque,
        "power": power
    }