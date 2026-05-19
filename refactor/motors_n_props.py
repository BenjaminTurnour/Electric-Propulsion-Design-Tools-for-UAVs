#Sweep the motors and props
#You need to generate prop&motor npz file using prop/motor_setup.py before running this file
#There are a few things that you can change in this file
# 1. constants: battery cell/esc efficiency
# 2. margins: current/voltage/rpm
# 3. prop size crop: current acceptable size is 5~30, larger range includes more props but increases memory usage.
# 4. valid combo mask. There might be conditions still missing: current condition masks include: 
#    prop_valid(if the prop can work under this v/thrust), v_min (motor limit), vmax(motor limit), imax(motor limit), rpm_max(motor limit)
# 5. Get a combo: change speed/thrust to get a best combo along with its power. This power will be higher than prop analysis alone. The reason is we consider both prop and motor limitations in this analysis.

import numpy as np
#import torch

#constants
cell_count = 12                      
esc_efficiency = 0.97
battery_voltage_limit = cell_count * 4.2  # V

#margin
current_margin = 1  #0.85
voltage_margin = 1  #0.85
rpm_margin = 1      #0.85 

def get_size(name):
    a=name.split("_")[1]
    a=a.split("x")[0]
    return int(a)

motors=[]
motor_names=[]
with np.load("motors.npz", allow_pickle=False) as f:
    #print(len(list(f.files)))
    for name in list(f.files): 
        motors.append(f[name])
        motor_names.append(name)
props=[]
prop_names=[]
with np.load("props.npz", allow_pickle=False) as f:
    #print(len(list(f.files)))
    for name in list(f.files): 
        if get_size(name)<=30 and get_size(name)>=5:  #prop size crop to reduce memory usage. drop small/large props
            if name=="PER3_27x13E":
                prev_best_prop=len(props)
            props.append(f[name])
            prop_names.append(name)

#target: motor*param + prop*v*thrust*param -> prop*motor*v*thrust*(prop_param+motor_param)
#motors
motors=np.array(motors) #motor num * kv,resistance,no_load_current_AperV,voltage_min,voltage_max,current_limit,rpm_limit,weight_g
#apply margin
motors[:,3]/=voltage_margin
motors[:,4]*=voltage_margin

v_limit_bat=np.array([battery_voltage_limit]*len(motors))
#print(v_limit_bat.shape,motors[:,4].shape)
motors[:,4]=np.minimum(motors[:,4],v_limit_bat) #battery limit/ motor limit whichever is smaller
motors[:,5]*=current_margin
#print(motor_names)

motors[:,6]*=rpm_margin
#some trnsform
motors[:,0]=60.0 / (2 * np.pi * motors[:,0]) #from kv to kt
#fix shape
temp=np.zeros((len(motors),3))
motors=np.concatenate((temp,motors), axis=1)
motors=motors.reshape(1,len(motors),1,1,-1)

# prop num * rpm_list,power_w,torque_nm  not used:j,pe,ct,cp, mach,fom
props=np.array(props)
props=props[:,:,:,:3]
temp=np.zeros((props.shape[0],props.shape[1],props.shape[2],8))
props=np.concatenate((props,temp),axis=-1)
props=props.reshape(props.shape[0],1,props.shape[1],props.shape[2],-1)

#to gpu (currently not applied)
#props=torch.from_numpy(props).cuda()
#motors=torch.from_numpy(motors).cuda()
prop_n_motor=props+motors
print(prop_n_motor.shape)

backEMF=prop_n_motor[:,:,:,:,0]*(np.pi/30.0)*prop_n_motor[:,:,:,:,3]
Iload=prop_n_motor[:,:,:,:,2]/prop_n_motor[:,:,:,:,3]
v_est=backEMF + Iload * prop_n_motor[:,:,:,:,4]
Itotal=prop_n_motor[:,:,:,:,5]*v_est+Iload

# power and efficiency
Pin = Itotal * v_est /esc_efficiency
Pout= Iload * backEMF
eff = Pout / Pin

#condition mask. some criteria might still be missing, like max battery current/prop mah <=0.7?
mask_prop=prop_n_motor[:,:,:,:,1]>0.0
#mask_vmin=v_est>=prop_n_motor[:,:,:,:,6]
mask_vmax=v_est<=prop_n_motor[:,:,:,:,7]
mask_imax=Itotal<=prop_n_motor[:,:,:,:,8]
mask_rpmmax=prop_n_motor[:,:,:,:,0]<=prop_n_motor[:,:,:,:,9]
mask_all=mask_prop & mask_vmax & mask_imax & mask_rpmmax
mask_fail=~mask_all
print(np.sum(mask_all),np.sum(mask_fail))
eff[mask_fail]=-1.0
Pin[mask_fail]=9999999.0 # invalid combo, set to max power 
#print(eff.shape)

#best combo among speed/thrust
Pin=Pin.reshape(Pin.shape[0] * Pin.shape[1], Pin.shape[2], Pin.shape[3])
best_pin = Pin.min(axis=0)                        # (V, T)
best_idx = Pin.argmin(axis=0)
best_prop_idx, best_motor_idx = np.unravel_index(best_idx, (len(prop_names),len(motor_names)))

#Get a combo
#This part is fast. All values have been calculated. Here we just retrieve them.
#You can use for loop to check different points all at once if you want
thrust=98 #N, 22 pound
t_idx=int(thrust) 
v=16 #ms, 35 mile/hour
v_idx=int(v)
print(prop_names[best_prop_idx[v_idx][t_idx]])  
print(motor_names[best_motor_idx[v_idx][t_idx]])
print(best_pin[v_idx][t_idx])


#verify numbers, you can ignore this part
#print("best prop, ignoring motors")
#print(mask_imax[prev_best_prop,:,v_idx,t_idx])
#print(mask_vmin[prev_best_prop,:,v_idx,t_idx])
#print(v_est[prev_best_prop,:,v_idx,t_idx])
#print(prop_n_motor[prev_best_prop,:,v_idx,t_idx,6])
#
#print(Itotal[prev_best_prop,:,v_idx,t_idx])
#print(Iload[prev_best_prop,:,v_idx,t_idx])
#print("best prop, considering motors")
#print(mask_imax[best_prop_idx[v_idx][t_idx],:,v_idx,t_idx])
#print(Itotal[best_prop_idx[v_idx][t_idx],:,v_idx,t_idx])
#print(Iload[best_prop_idx[v_idx][t_idx],:,v_idx,t_idx])


#Plot the power distribution of different v/thrust
#Each point is the power of the best combo given v/thrust
# import matplotlib.pyplot as plt
# import matplotlib.colors as mcolors
# cmin, cmax = 0.0, 5000.0   
# norm = mcolors.Normalize(vmin=cmin, vmax=cmax, clip=True)
# vmin, vmax = 0.0, 80.0 #m/s
# thrust_min, thrust_max=0.0,140.0 #N
# extent = [vmin, vmax, thrust_min, thrust_max]
# plt.imshow(best_pin,
#            cmap='viridis',
#            origin='lower',
#            extent=extent,     
#            aspect='auto',
#            norm=norm)      
# plt.colorbar(label='Best Power Combo')      
# plt.xlabel('Velocity (m/s)')
# plt.ylabel('Thrust (N)')
# plt.title('Power over Velocity–Thrust')
# plt.show()


#Plot the power distribution of different v/thrust
#Each point is the power of the best combo given v/thrust
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

cmin, cmax = 0.0, 5000.0   
norm = mcolors.Normalize(vmin=cmin, vmax=cmax, clip=True)
vmin, vmax = 0.0, 80.0 #m/s
thrust_min, thrust_max=0.0,140.0 #N
extent = [vmin, vmax, thrust_min, thrust_max]

plt.figure()  # ADDED: create a figure explicitly
im = plt.imshow(best_pin,
                cmap='viridis',
                origin='lower',
                extent=extent,
                aspect='auto',
                norm=norm)      
plt.colorbar(im, label='Best Power Combo')  # CHANGED: tie colorbar to the image
plt.xlabel('Velocity (m/s)')
plt.ylabel('Thrust (N)')
plt.title('Power over Velocity–Thrust')
plt.tight_layout()  # ADDED: layout
plt.savefig("power_map.png", dpi=200, bbox_inches="tight")  # ADDED: always save
print("Saved: power_map.png")  # ADDED: confirm
plt.show()
