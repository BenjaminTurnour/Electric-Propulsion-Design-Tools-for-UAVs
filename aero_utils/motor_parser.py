import csv
import os
from dataclasses import dataclass

@dataclass
class PhysicsMotorModel:
    motor_name: str
    kv: float                       # RPM/V
    resistance: float               # Ohms
    no_load_current_AperV: float    # Amps
    voltage_min: float              # Volts
    voltage_max: float              # Volts
    current_limit: float            # Amps
    rpm_limit: float                # RPM
    weight_g: float                 # Grams

def load_motor_models() -> dict[str, PhysicsMotorModel]:
    folder = os.path.join(os.path.dirname(__file__), "..", "motors")
    folder = os.path.abspath(folder)
    models = {}

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

                    models[name] = PhysicsMotorModel(
                        motor_name=name,
                        kv=kv,
                        resistance=resistance,
                        no_load_current_AperV=no_load_current_AperV,
                        voltage_min=voltage_min,
                        voltage_max=voltage_max,
                        current_limit=current_limit,
                        rpm_limit=rpm_limit,
                        weight_g=weight_g
                    )
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

    return models
