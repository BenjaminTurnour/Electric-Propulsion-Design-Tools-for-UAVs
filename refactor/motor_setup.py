# setup motor data
# most of the code is inherited from motor_parser.py
# save the motor data in an npz file
# npz file is similar to python dict. motor_name->parameter_array
# parameter_array is a list of numbers in the following order
# kv,resistance,no_load_current_AperV,voltage_min,voltage_max,current_limit,rpm_limit,weight_g
# I don't think you have to change this file.
import csv
import os
import pandas as pd
import numpy as np
def load_motor_models():
    folder = os.path.join(os.path.dirname(__file__), "..", "motors")
    folder = os.path.abspath(folder)
    motors={}
    for filename in os.listdir(folder):
        if filename.endswith(".csv"):
            path = os.path.join(folder, filename)
            try:
                with open(path, newline='', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    data = next(reader)
                    name = data["motor_name"]
                    kv = float(data["kv"])
                    resistance = float(data["resistance_mohm"]) / 1000
                    no_load_current_AperV = float(data["no_load_current_AperV"])
                    voltage_min = float(data["voltage_min"])
                    voltage_max = float(data["voltage_max"])
                    current_limit = float(data["current_limit"])
                    rpm_limit = float(data["rpm_limit"]) if data.get("rpm_limit", "").strip() else kv * voltage_max
                    weight_g = float(data["weight_g"])
                    motors[name]=np.array([kv,resistance,no_load_current_AperV,voltage_min,voltage_max,current_limit,rpm_limit,weight_g])
            except Exception as e:
                print(f"Failed to load {filename}: {e}")
    np.savez_compressed("motors.npz", **motors)
if __name__ == "__main__":
    load_motor_models()