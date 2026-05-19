# ---------------------------------------------------------------------
# SUMMARY:
# This module is used to load and parse APC propeller data files (*.dat).
#
# It defines two data structures:
#   - PropellerDataBlock: Holds performance data at a specific RPM.
#   - PropellerProfile: A collection of PropellerDataBlocks representing a full propeller dataset.
#
# Main functions:
#   - parse_apc_dat_file(filepath): Reads one APC .dat file and returns a PropellerProfile.
#   - load_all_propellers(directory): Loads and parses all .dat files in a folder.
# ---------------------------------------------------------------------

import os
import numpy as np
from dataclasses import dataclass
from typing import List

# This class holds performance data at a single RPM setting for a propeller
@dataclass
class PropellerDataBlock:
    rpm: int                         # The RPM at which the data was collected
    v: np.ndarray                    # Airspeed in m/s
    j: np.ndarray                    # Advance ratio
    pe: np.ndarray                   # Mechanical efficiency
    ct: np.ndarray                   # Thrust coefficient
    cp: np.ndarray                   # Power coefficient
    power_w: np.ndarray              # Power input in watts
    torque_nm: np.ndarray            # Torque in Newton-meters
    thrust_n: np.ndarray             # Thrust in Newtons
    fom: np.ndarray                  # Figure of merit (overall efficiency)

# This class holds all RPM blocks for a single propeller profile
@dataclass
class PropellerProfile:
    name: str                        # File name of the propeller data (e.g., "PER3_10x5")
    blocks: List[PropellerDataBlock]# List of data blocks, one for each RPM tested

# This function reads one .dat file and parses it into a PropellerProfile
def parse_apc_dat_file(filepath: str) -> PropellerProfile:
    name = os.path.basename(filepath).split(".")[0]  # Extract filename without extension
    blocks = []  # List to hold data blocks at different RPMs

    # Read all lines from the file
    with open(filepath, "r") as f:
        lines = f.readlines()

    i = 17  # Skip the header (first 17 lines are metadata)

    # Loop through the file line by line
    while i < len(lines):
        line = lines[i].strip()

        # Look for the start of a new RPM data block
        if line.startswith("PROP RPM"):
            try:
                rpm = int(line.split("=")[-1].strip())  # Extract RPM value
            except ValueError:
                i += 1  # Skip line if RPM is invalid
                continue

            i += 3  # Skip next 3 lines (column headers and units)

            # Initialize lists to hold each column of data
            v, j, pe, ct, cp = [], [], [], [], []
            power_w, torque_nm, thrust_n, fom = [], [], [], []

            # Read each line of data in this block
            while i < len(lines):
                data_line = lines[i].strip()
                if not data_line or "PROP RPM" in data_line:
                    # Stop when reaching an empty line or next block
                    break

                parts = data_line.split()
                if len(parts) >= 15:
                    try:
                        # Extract the relevant columns (by position)
                        v.append(float(parts[0]))           # Airspeed
                        j.append(float(parts[1]))           # Advance ratio
                        pe.append(float(parts[2]))          # Efficiency
                        ct.append(float(parts[3]))          # Thrust coefficient
                        cp.append(float(parts[4]))          # Power coefficient
                        power_w.append(float(parts[8]))     # Power (watts)
                        torque_nm.append(float(parts[9]))   # Torque (Nm)
                        thrust_n.append(float(parts[10]))   # Thrust (N)
                        fom.append(float(parts[14]))        # Figure of merit
                    except ValueError:
                        # If a line fails to parse, skip it
                        pass

                i += 1  # Move to next line

            # Create a data block from collected arrays
            block = PropellerDataBlock(
                rpm=rpm,
                v=np.array(v),
                j=np.array(j),
                pe=np.array(pe),
                ct=np.array(ct),
                cp=np.array(cp),
                power_w=np.array(power_w),
                torque_nm=np.array(torque_nm),
                thrust_n=np.array(thrust_n),
                fom=np.array(fom),
            )
            blocks.append(block)  # Add block to profile
        else:
            i += 1  # Skip lines that are not data blocks

    return PropellerProfile(name=name, blocks=blocks)

# This function loads and parses all .dat files in a directory
def load_all_propellers(directory: str) -> List[PropellerProfile]:
    profiles = []  # List to hold all loaded propeller profiles
    for file in os.listdir(directory):
        if file.endswith(".dat"):
            try:
                path = os.path.join(directory, file)
                profile = parse_apc_dat_file(path)  # Parse the file
                profiles.append(profile)           # Add to the list
            except Exception as e:
                # If any error occurs, print a message and continue
                print(f"Failed to load {file}: {e}")
    return profiles
