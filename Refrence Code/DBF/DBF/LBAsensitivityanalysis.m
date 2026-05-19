clear all;
close all;
clc;
set(0,'DefaultFigureWindowStyle','docked');

pyenv(Version="/Users/codykarcher/software/miniconda3/bin/python");
python_data = pyrunfile('analyze_propeller.py','opt');
thrust_output = double(python_data);

% Column 1:  Flight Velocity in Mile per Hour
% Column 2:  Thrust in lbf
% Column 3:  RPM

data = thrust_output;

function res = residuals(vguess,W_pl,S,data)
    rho = 23.769e-4;
    Cdo = 0.013;
    b = 6;
    e = 0.9;
    V=vguess*1.467;
    W = 7.09 + 3*0.067*(2.05*S)^(3/2) + W_pl;
    
    rhs = 0.5*rho*V^2*(Cdo+((4*W^2)/(pi*e*b^2*rho^2*V^4*S)))*S;
    lhs = interp1(data(:,1),data(:,2),vguess,"cubic");
    res = (lhs - rhs)^2;
    %res = lhs - rhs; 
end

s_array=linspace(0.01,30,50);
w_array=linspace(0.01,20,30);
[ss,ww]=meshgrid(s_array,w_array);
vv=0.*ss;

grid_dims=size(ss);
options = optimoptions('fminunc','Display','off');
for i=1:grid_dims(1)
    for j=1:grid_dims(2)
        W_pl=ww(i,j);
        S=ss(i,j);
        f = @(vguess)residuals(vguess,W_pl,S,data);
        [res,fval,exitflag,output] = fminunc(f,100,options); %res is velocity here only
        rpm = interp1(data(:,1),data(:,3),res,"cubic");
        if exitflag>0 && fval<=1e-8 %&& rpm<=9000
            vv(i,j)=res;
        else 
            vv(i,j)=NaN;
        end
    end 
end

contourf(ss,ww,vv)
colorbar;


% vguess_array = linspace(0,150,151);
% S = 15;
% W_pl = 10;
% f = @(vguess)residuals(vguess,W_pl,S,data);

% options = optimoptions('fminunc','Display','off');
% [res,fval,exitflag,output] = fminunc(f,100,options);
% [res,fval,exitflag,output] = fminunc(f,100);
% disp(res)
% disp(fval)
% disp(exitflag)
% disp(7.09 + 0.067*(2.05*S)^(3/2) + W_pl)
% rpm = interp1(data(:,1),data(:,3),res,"cubic");
% disp(rpm)

% err_arr = [];
% 
% for i = 1: length(vguess_array)
%     err_arr(i) = f(vguess_array(i));
% 
% 
% end
% figure(1)
% hold on
% plot(vguess_array,err_arr)
% ylim([-1 1])
% yline(0)