import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aero_utils.motor_parser import load_motor_models
from aero_utils.propdata_interp import get_prop_data

# This function retrieves propeller data for a given propeller name, velocity, and thrust.

motors = load_motor_models()

# Values for propeller
velocity = 33    #velocity in m/s
thrust = 140      #thrust in N

#values for motor
propData = get_prop_data("18x12E", velocity, thrust)

for name,motor in motors.items():
    print(name,motor.kv)
    angularSpeed = (propData['rpm']/60)*2*np.pi             # Convert RPM to radians per second
    kt = 60/(2*np.pi*motor.kv)                              # Convert kv to torque constant in Nm/A 
    Iload = propData['torque']/kt                           # Calculate current load in Amps
    backEMF = angularSpeed * kt                             # Back EMF in Volts
    v_est = backEMF + Iload * motor.resistance              # Estimated voltage across motor
    Itotal = Iload + (motor.no_load_current_AperV * v_est)  # Total current including no-load current
    Pin = Itotal * v_est                                    # Power input in Watts
    Pout = propData['torque'] * angularSpeed                # Power output from propeller data
    efficiency = Pout / Pin                                 # Calculate efficiency

    Vrequired = angularSpeed * kt + Iload * motor.resistance    # Voltage required to spin prop at given speed and load

    current_linit_margin = motor.current_limit * 0.85
    voltage_max_margin = motor.voltage_max * 0.85

    if Itotal > motor.current_limit:
        print(f"Motor {name} exceeds current limit with {Itotal:.2f} A")
    elif Itotal > current_linit_margin:
        print(f"Motor {name} is nearing current limit with {Itotal:.2f} A")
    else:
        print(f"Motor {name} is within current limit with {Itotal:.2f} A")
    
    if v_est > motor.voltage_max:
        print(f"Motor {name} exceeds voltage limit with {v_est:.2f} V")
    elif v_est > voltage_max_margin:
        print(f"Motor {name} is nearing voltage limit with {v_est:.2f} V")
    else:
        print(f"Motor {name} is within voltage limit with {v_est:.2f} V")

    print(f"efficency: {efficiency:.2f}")
    print(f"v_est: {v_est:.2f}")
    print(" ")