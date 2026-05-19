# Refactor

## Setup
Before continuing, set up the data:
```bash
python prop_setup.py
python motor_setup.py
```
You should see motors.npz and props.npz in the folder after this.

## Plot: Power vs Prop Size
Plot power vs propeller size given v/thrust (does not consider motor limitation)
```bash
python power_vs_size.py
```

## Sweep: Motors and Props
Sweep motors and props to find the best combo
```bash
python motors_n_props.py
```
