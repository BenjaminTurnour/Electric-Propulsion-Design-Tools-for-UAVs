# Aircraft-Sizing
This repository will include all the code and files needed to make initial sizing and design choices for the AIAA Design Build Fly competition.

Sparse Checkout recommended if you are low on storage space:

```
cd <desired_parent_directory>
mkdir Aircraft-Sizing
cd Aircraft-Sizing
git init
git remote add -f origin git@github.com:CSULB-DBF/Aircraft-Sizing.git
git config core.sparseCheckout true
echo "README.md" >> .git/info/sparse-checkout
echo "motor_check.py" >> .git/info/sparse-checkout
echo "StrutureTest.py" >> .git/info/sparse-checkout
echo "xfoil_example.py" >> .git/info/sparse-checkout
echo "propeller_plots.py" >> .git/info/sparse-checkout
echo "compare_motors.py" >> .git/info/sparse-checkout
echo "outputPower.py" >> .git/info/sparse-checkout
echo "polars/" >> .git/info/sparse-checkout
echo "motors/" >> .git/info/sparse-checkout
echo "Mission_Score_Calculators/" >> .git/info/sparse-checkout
echo "extra_tools/" >> .git/info/sparse-checkout
echo "design_Transport/" >> .git/info/sparse-checkout
echo "BMI_Chart/" >> .git/info/sparse-checkout
echo "APC/" >> .git/info/sparse-checkout
echo "aero_utils/" >> .git/info/sparse-checkout
echo "dbf_airplane.ipynb" >> .git/info/sparse-checkout
git pull origin main
git branch --set-upstream-to=origin/main
``` 

Property of CSULB's AIAA DBF team.
