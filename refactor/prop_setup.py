# prosetup
# inherited from propdata_parser.py
# read in all APC prop files and save them in an npz file
# npz file: propname->parameter array
# paramter array is a 3d array in the following shape
# 81*141*9
# where 81 is velocity index, 5 means 5m/s
# 141 is the thrust index 20 means 20N
# note that the precision is set to 1, meaning that there's not 15.5m/s. Pick a close number 15 or 16 instead.
# 9 means 9 different parameters responding to different speed and thrust
# the 9 parameters are in the following order
# rpm,power_w,torque_nm,j,pe,ct,cp, mach,fom
# You can change the file if you want a different search range of thrust and speed

import os
import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt

def parse_apc_dat_file(filepath):
    name = os.path.basename(filepath).split(".")[0]  
    vmin, vmax = 0.0, 80.0 #m/s
    thrust_min, thrust_max=0.0,140.0 #N
    v_grid = np.linspace(vmin, vmax, 81)
    t_grid = np.linspace(thrust_min, thrust_max, 141)
    Vg, Tg = np.meshgrid(v_grid, t_grid, indexing="ij")
    rpm_list=[]
    v, j, pe, ct, cp = [], [], [], [], []
    power_w, torque_nm, thrust_n, mach, fom = [], [], [], [], []
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
                        v.append(float(parts[0])*0.44704)   # Airspeed m/s
                        j.append(float(parts[1]))           # Advance ratio
                        pe.append(float(parts[2]))          # Efficiency
                        ct.append(float(parts[3]))          # Thrust coefficient
                        cp.append(float(parts[4]))          # Power coefficient
                        power_w.append(float(parts[8]))     # Power (watts)
                        torque_nm.append(float(parts[9]))   # Torque (Nm)
                        thrust_n.append(float(parts[10]))   # Thrust (N)
                        mach.append(float(parts[12]))
                        fom.append(float(parts[14]))        # Figure of merit
                        rpm_list.append(float(rpm))         # RPM
                    except ValueError:
                        # If a line fails to parse, skip it
                        pass
                i += 1  # Move to next line
            # a pack 
        else:
            i += 1  # Skip lines that are not data blocks
    param=[rpm_list,power_w,torque_nm,j,pe,ct,cp, mach,fom]
    #print(len(rpm_list),len(power_w),len(torque_nm),len(j),len(pe),len(ct),len(cp),len(fom))
    v=np.array(v)
    thrust_n=np.array(thrust_n)
    param=np.array(param).T
    ans = griddata(points=np.c_[v, thrust_n], values=param, xi=(Vg, Tg),method="linear", fill_value=-1.0)    # shape: (nv, np, K)
    return name,ans

# This function loads and parses all .dat files in a directory
def load_all_propellers(directory: str):
    all_prop={}
    for file in os.listdir(directory):
        if file.endswith(".dat"):
            try:
                path = os.path.join(directory, file)
                name, data = parse_apc_dat_file(path)  # Parse the file
                all_prop[name]=data.astype(np.float32)
            except Exception as e:
                # If any error occurs, print a message and continue
                print(f"Failed to load {file}: {e}")
        
    np.savez_compressed("props.npz", **all_prop)
if __name__ == "__main__":
    load_all_propellers("APC")

    #Test code: reading the saved npz file
    #with np.load("props.npz", allow_pickle=False) as f:
    #    print(len(list(f.files)))
    #    for name in list(f.files): 
    #        print(name,f[name].shape)
        
    #Test code: reading 1 prop data and plot its parameters
    #name,ans=parse_apc_dat_file("..\APC\PER3_16x8E.dat")
    #rpm_graph=ans[:,:,0]
    #vmin, vmax = 0.0, 140.0 #m/s
    #thrust_min, thrust_max=0.0,180.0 #N
    #extent = [vmin, vmax, thrust_min, thrust_max]
    #plt.imshow(rpm_graph,
    #           cmap='viridis',
    #           origin='lower',
    #           extent=extent,      # <- map pixels to (velocity, thrust)
    #           aspect='auto')      # avoid square pixels if ranges differ
    #plt.colorbar(label='RPM')      # or whichever quantity you plotted
    #plt.xlabel('Velocity (m/s)')
    #plt.ylabel('Thrust (N)')
    #plt.title('RPM over Velocity–Thrust')
    #plt.show()
    #rpm_graph=ans[:,:,1]
    #plt.imshow(rpm_graph,
    #           cmap='viridis',
    #           origin='lower',
    #           extent=extent,      # <- map pixels to (velocity, thrust)
    #           aspect='auto')      # avoid square pixels if ranges differ
    #plt.colorbar(label='Power')      # or whichever quantity you plotted
    #plt.xlabel('Velocity (m/s)')
    #plt.ylabel('Thrust (N)')
    #plt.title('Power over Velocity–Thrust')
    #plt.show()
    #rpm_graph=ans[:,:,2]
    #plt.imshow(rpm_graph,
    #           cmap='viridis',
    #           origin='lower',
    #           extent=extent,      # <- map pixels to (velocity, thrust)
    #           aspect='auto')      # avoid square pixels if ranges differ
    #plt.colorbar(label='Torque')      # or whichever quantity you plotted
    #plt.xlabel('Velocity (m/s)')
    #plt.ylabel('Thrust (N)')
    #plt.title('Torque over Velocity–Thrust')
    #plt.show()