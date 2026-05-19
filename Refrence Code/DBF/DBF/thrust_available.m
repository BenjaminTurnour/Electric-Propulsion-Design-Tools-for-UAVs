clear all;
close all;
clc;

rho = 23.679e-4;
Cdo = 0.013;
b = 6;
e = 0.9;

varr = linspace(1,250,100);
darr = [];
W_pl = 20;
S = 7;
W = 7.09 + 0.067*(2.05*S)^(3/2) + W_pl ;

hold on
carr = [];
for i=1:length(varr)
    vguess=varr(i);
    V = vguess;
    cl = W/(0.5 * rho * V^2 * S);
    carr(i) = cl;

    D = 0.5 * rho * V^2 * ( Cdo + ((4*W^2)/(pi*e*b^2*rho^2*V^4*S)) ) * S;
    darr(i) = D;
end

plot(varr,darr,'color','blue');

parr = linspace(500,4000,5);
for i=1:length(parr)
    power_setting = parr(i);
    fl = sprintf('p_500.py %g',power_setting);
    data = double(pyrunfile(fl,'opt'));
    % plot(data(:,1),data(:,2),'color','green')%,'alpha',power_setting/4000)
    plot(data(:,1),data(:,2),'color',[0,.3,0,power_setting/4000])
end
% 
power_setting = 1800;
fl = sprintf('p_500.py %g',floor(power_setting));
data = double(pyrunfile(fl,'opt'));
plot(data(:,1),data(:,2),'color','red')
plot(data(:,1),data(:,3)/1000,'color','black')

plot(varr,10*carr,'color','magenta')

ylim([0,20])
ylabel('Drag')
xlabel('Velocity')

grid on







varr = linspace(1,250,100);
darr = [];
W_pl = 0;
W = 7.09 + 0.067*(2.05*S)^(3/2) + W_pl ;

hold on
carr = [];
for i=1:length(varr)
    vguess=varr(i);
    V = vguess;
    cl = W/(0.5 * rho * V^2 * S);
    carr(i) = cl;

    D = 0.5 * rho * V^2 * ( Cdo + ((4*W^2)/(pi*e*b^2*rho^2*V^4*S)) ) * S;
    darr(i) = D;
end

plot(varr,darr,'color','cyan');
plot(varr,10*carr,'color',[1,.5,0])

hold off