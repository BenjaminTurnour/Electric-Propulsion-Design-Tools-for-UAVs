clear all
close all
clc

pyenv(Version="/Users/codykarcher/software/miniconda3/bin/python");
python_data = pyrunfile('analyze_propeller.py','opt');
thrust_output = double(python_data);
disp(thrust_output)

% Column 1:  Flight Velocity in Mile per Hour
% Column 2:  Thrust in lbf
% Column 3:  RPM