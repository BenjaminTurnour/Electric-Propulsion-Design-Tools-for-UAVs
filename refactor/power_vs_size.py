# This is a power vs size analysis based on prop data alone
# You need to generate prop npz file using prop setup.py before running this file
# Change thrust, currently 98, and v, currently 16 to whichever number you want
# but make sure these two number is within the range you set in prop setup.py
# The plot shows the power of props of different sizes givent v/thrust
# In addition, it prints out the top 10 props with lowest power givent v/thrust

import numpy as np
import matplotlib.pyplot as plt
from heapq import heappush, heappop

#v/thrust setting
thrust=98 #N, 22 pound
t_idx=int(thrust) # step=2
v=16 #m/s, 35 mile/hour
v_idx=int(v)



def get_size(name):
    a=name.split("_")[1]
    a=a.split("x")[0]
    return int(a)
data=[]
heap=[]
with np.load("props.npz", allow_pickle=False) as f:
    for name in list(f.files): 
        #param=[rpm_list,power_w,torque_nm,j,pe,ct,cp,fom]
        s=get_size(name)
        #print(f[name][v_idx][t_idx][1])
        if f[name][v_idx][t_idx][1]>0:
            heappush(heap,(f[name][v_idx][t_idx][1],name))
            data.append([s,f[name][v_idx][t_idx][1]])
        #break
for i in range(10):
    power,name=heappop(heap)
    print(name,power)
data=np.array(data)
#print(data.shape)
x=data[:,0]
#print(x.shape)
y=data[:,1]
#print(y.shape)
plt.scatter(x, y)
plt.xlim(0, 50)
# Add title and labels
plt.title("Power/Size Plot")
plt.xlabel("size")
plt.ylabel("power")

# Display the plot
plt.show()