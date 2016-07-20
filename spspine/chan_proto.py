"""\
Create general Channel Proto, pass in name, x and y power, and params

Also, create the library of channels
Might need a few other chan_proto types, such as
     inf-tau channels
     Ca dep channels
chan_proto quires alpha and beta params for both activation and inactivation
If no inactivation, just send in empty Yparam array.
"""

from __future__ import print_function, division
import moose
import numpy as np

from spspine.graph import plot_channel
from spspine import param_cond, param_chan, param_sim

VMIN = -120e-3
VMAX = 50e-3
VDIVS = 3401 #0.5 mV steps
CAMIN=0.01e-3   #10 nM
CAMAX=40e-3  #40 uM, might want to go up to 100 uM with spines
CADIVS=4001 #10 nM steps

def interpolate_values_in_table(tabA,V_0,l=40):
    '''This function interpolates values in the table
    around tabA[V_0]. '''
    V = np.linspace(VMIN, VMAX, len(tabA))
    idx =  abs(V-V_0).argmin()
    A_min = tabA[idx-l]
    V_min = V[idx-l]
    A_max = tabA[idx+l]
    V_max = V[idx+l]
    a = (A_max-A_min)/(V_max-V_min)
    b = A_max - a*V_max
    tabA[idx-l:idx+l] = V[idx-l:idx+l]*a+b
    return tabA

def fix_singularities(Params,Gate):
    
    if Params.A_C < 0:

        V_0 = Params.A_vslope*np.log(-Params.A_C)-Params.Avhalf

        if V_0 > VMIN and V_0 < VMAX:
            #change values in tableA and tableB, because tableB contains sum of alpha and beta
            tabA = interpolate_values_in_table(Gate.tableA,V_0)
            tabB = interpolate_values_in_table(Gate.tableB,V_0)
            Gate.tableA = tabA
            Gate.tableB = tabB

    if Params.B_C < 0:

        V_0 = Params.B_vslope*np.log(-Params.B_C)-Params.Bvhalf

        if V_0 > VMIN and V_0 < VMAX:
            #change values in tableB
            tabB = interpolate_values_in_table(Gate.tableB,V_0)
            Gate.tableB = tabB

    return Gate

#may need a CaV channel if X gate uses alpha,beta and Ygate uses inf tau
#Or, have Y form an option - if in tau, do something like NaF
def chan_proto(chanpath,params,Xparams,Yparams,Zparams=None):
    if param_sim.printinfo:
        print(chanpath, ":", params)
    chan = moose.HHChannel(chanpath)
    chan.Xpower = params.Xpow
    if params.Xpow > 0:
        xGate = moose.HHGate(chan.path + '/gateX')
        xGate.setupAlpha(Xparams + [VDIVS, VMIN, VMAX])
        xGate = fix_singularities(Xparams,xGate)

    chan.Ypower = params.Ypow
    if params.Ypow > 0:
        yGate = moose.HHGate(chan.path + '/gateY')
        yGate.setupAlpha(Yparams + [VDIVS, VMIN, VMAX])
        yGate = fix_singularities(Yparams,yGate)
    if params.Zpow > 0:
        chan.Zpower = params.Zpow
        zgate = moose.HHGate(chan.path + '/gateZ')
        ca_array = np.linspace(CAMIN, CAMAX, CADIVS)
        zgate.min=CAMIN
        zgate.max=CAMAX
        caterm=(ca_array/Zparams.Kd)**Zparams.power
        inf_z=caterm/(1+caterm)
        tau_z=Zparams.tau*np.ones(len(ca_array))
        zgate.tableA=inf_z / tau_z
        zgate.tableB=1 / tau_z
        chan.useConcentration=True
        #moose.showfield(zgate)
    #end if Zpow
    chan.Ek = params.Erev
    return chan

def NaFchan_proto(chanpath,params,Xparams,Yparams):
    v_array = np.linspace(VMIN, VMAX, VDIVS)
    chan = moose.HHChannel(chanpath)
    chan.Xpower = params.Xpow #creates the m gate
    mgate = moose.HHGate(chan.path + '/gateX')
    #probably can replace the next 3 lines with mgate.setupTau (except for problem with tau_x begin quadratic)
    mgate.min=VMIN
    mgate.max=VMAX
    inf_x = Xparams.Arate/(Xparams.A_C + np.exp(( v_array+Xparams.Avhalf)/Xparams.Avslope))
    tau1 = Xparams.tauVdep/(1+np.exp((v_array+Xparams.tauVhalf)/Xparams.tauVslope))
    tau2 = Xparams.tauVdep/(1+np.exp((v_array+Xparams.tauVhalf)/-Xparams.tauVslope))
    tau_x = (Xparams.taumin+1000*tau1*tau2)/param_chan.qfactNaF
    if param_sim.printMoreInfo:
        print("NaF mgate:", mgate, 'tau1:', tau1, "tau2:", tau2, 'tau:', tau_x)

    mgate.tableA = inf_x / tau_x
    mgate.tableB =  1 / tau_x
#    moose.showfield(mgate)

    chan.Ypower = params.Ypow #creates the h gate
    hgate = moose.HHGate(chan.path + '/gateY')
    hgate.min=VMIN
    hgate.max=VMAX
    tau_y=(Yparams.taumin+(Yparams.tauVdep/(1+np.exp((v_array+Yparams.tauVhalf)/Yparams.tauVslope))))/param_chan.qfactNaF
    inf_y=Yparams.Arate/(Yparams.A_C + np.exp(( v_array+Yparams.Avhalf)/Yparams.Avslope))
    if param_sim.printMoreInfo:
        print("NaF hgate:", hgate, 'inf:', inf_y, 'tau:', tau_y)
    hgate.tableA = inf_y / tau_y
    hgate.tableB = 1 / tau_y
    chan.Ek=params.Erev
    return chan

def BKchan_proto(chanpath,params,gateParams):

    ZFbyRT=2*param_cond.Faraday/(param_cond.R*(param_cond.Temp+273.15))
    v_array = np.linspace(VMIN, VMAX, VDIVS)
    ca_array = np.linspace(CAMIN, CAMAX, CADIVS)
    if VDIVS<=5 and CADIVS<=5 and param_sim.printinfo:
        print(v_array,ca_array)
    gatingMatrix = []
    for i,pars in enumerate(gateParams):
        Vdepgating=pars.K*np.exp(pars.delta*ZFbyRT*v_array)
        if i == 0:
            gatingMatrix.append(pars.alphabeta*ca_array[None,:]/(ca_array[None,:]+pars.K*Vdepgating[:,None]))
            #table.tableVector2D=gatingMatrix
        else:
            gatingMatrix.append(pars.alphabeta/(1+ca_array[None,:]/pars.K*Vdepgating[:,None]))
            gatingMatrix[i] += gatingMatrix[0]
            #table.tableVector2D=gatingMatrix


    chan = moose.HHChannel2D(chanpath)
    chan.Xpower = params.Xpow
    chan.Ek=params.Erev
    chan.Xindex="VOLT_C1_INDEX"
    xGate = moose.HHGate2D(chan.path + '/gateX')
    xGate.xminA=xGate.xminB=VMIN
    xGate.xmaxA=xGate.xmaxB=VMAX
    xGate.xdivsA=xGate.xdivsB=VDIVS
    xGate.yminA=xGate.yminB=CAMIN
    xGate.ymaxA=xGate.ymaxB=CAMAX
    xGate.ydivsA=xGate.ydivsB=CADIVS
    xGate.tableA=gatingMatrix[0]
    xGate.tableB=gatingMatrix[1]
    if param_sim.printinfo:
        print(chan.path)
        for ii in np.arange(0, VDIVS,1000):
            print("V=", VMIN+ii*(VMAX-VMIN)/(VDIVS-1))
            for jj in np.arange(0,CADIVS,1000):
                print("    Ca=", CAMIN+jj*(CAMAX-CAMIN)/(CADIVS-1), "A,B=", xGate.tableA[ii][jj],xGate.tableB[ii][jj])
    return chan
#ChanDict (param_chan.py) includes channel function name in the dictionary


#*params... passes the set of values not as a list but as individuals
def make_channel(chanpath,params):
    if params[0] == 'typical_1D_alpha':
        return chan_proto(chanpath,*params[1:])
    elif params[0] == 'atypical_1D':
        return NaFchan_proto(chanpath,*params[1:])
    elif params[0] == '2D':
        return BKchan_proto(chanpath,*params[1:])
    else:
        sys.exit('Exiting. Could not find channel '+params[0] +' proto function for channel '+chanpath)

def chanlib(plotchan,plotpow):
    if not moose.exists('/library'):
        moose.Neutral('/library')
    #Adding all the channels to the library. *list removes list elements from the list,
    #so they can be used as function arguments
    chan = [make_channel('/library/'+key, value) for key, value in param_chan.ChanDict.items()]
    if param_sim.ghkYesNo:
        ghk=moose.GHK('/library/ghk')
        ghk.T=param_cond.Temp
        ghk.Cout=param_cond.ConcOut
        ghk.valency=2
    #
    if plotchan:
        for libchan in chan:
            plot_channel.plot_gate_params(libchan,plotpow, VMIN, VMAX, CAMIN, CAMAX)
