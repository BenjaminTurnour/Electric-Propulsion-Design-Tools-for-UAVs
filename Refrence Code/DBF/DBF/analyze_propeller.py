import numpy as np
import scipy.optimize as spo

p_mg = 2200

f = open('PER3_16x16.dat','r')
data = f.read()
f.close()

rpm_blocks = data.split('PROP RPM')

headers = ['V','J','Pe','Ct','Cp','PWR_S','Torque_S','Thrust_S','PWR_M','Torque_M','Thrust_M','THR/PWR','Mach','Reyn','FOM']
units = ['(mph)','(Adv_Ratio)','-','-','-','(Hp)','(In-Lbf)','(Lbf)','(W)','(N-m)','(N)','(g/W)','-','-','-']

read_data = {}

for block in rpm_blocks[1:]:
    lines = block.split('\n')
    rpm_value = None
    for ln in lines:
        if '=' in ln:
            ents = ln.split()
            rpm_value = float(ents[1])
            temp_row = []
            for i in range(0,len(headers)):
                temp_row.append([])
            read_data[rpm_value] = dict(zip(headers,temp_row))
        else:
            ents = ln.split()
            if len(ents)>0:
                if ents[0] == 'V':
                    # headers in line
                    pass
                elif ents[0] == '(mph)':
                    #units line
                    pass
                else:
                    # print(ents)
                    if len(ents) == len(headers):
                        for i, ent in enumerate(ents):
                            read_data[rpm_value][headers[i]].append( float(ent) )

V_array = np.linspace(0,218,219)

tbl = {}

for v in V_array:
    valid_rpms = []
    for rpm, dta in read_data.items():
        if v >= dta['V'][0] and v <= dta['V'][-1]:
            valid_rpms.append(rpm)

    if len(valid_rpms) > 1:
        tbl[v] = {}
        tbl[v]['Thrust_M'] = []
        tbl[v]['Torque_M'] = []
        tbl[v]['RPM']      = valid_rpms

        for rpm in valid_rpms:
            Thrust_M = np.interp(v, read_data[rpm]['V'], read_data[rpm]['Thrust_M'])
            Torque_M = np.interp(v, read_data[rpm]['V'], read_data[rpm]['Torque_M'])
            tbl[v]['Thrust_M'].append(Thrust_M)
            tbl[v]['Torque_M'].append(Torque_M)

v_mg = np.linspace(0,180,91)

def residual(x,p,rpm,trq):
    trq_val = np.interp(x,rpm,trq)
    p_val = trq_val * (x*2*np.pi/60)
    return 100*(p_val - p)

thrust = np.zeros(len(v_mg))
rpms   = np.zeros(len(v_mg))
for i,v in enumerate(v_mg):
    res = spo.root(residual, 8000 ,args=(p_mg,tbl[v]['RPM'],tbl[v]['Torque_M']))
    if res['message'] == 'The solution converged.' or res['fun'] < 1e-10:
        rpm_balanced = res['x'][0]
    else:
        raise RuntimeError('Failed to find valid solution')
    rpms[i] = rpm_balanced
    thrust[i] = np.interp(rpm_balanced, tbl[v]['RPM'], tbl[v]['Thrust_M'] )

thrust *= 0.224809 # convert from newtons to pounds-force

opt = np.array([v_mg,thrust, rpms]).T





