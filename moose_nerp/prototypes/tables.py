from __future__ import print_function, division
import moose
import numpy as np

from collections import defaultdict, namedtuple
#from moose_nerp.prototypes.calcium import NAME_CALCIUM
from moose_nerp.prototypes.spines import NAME_HEAD
from moose_nerp.prototypes.connect import CONNECT_SEPARATOR
from . import util
DATA_NAME='/data'
HDF5WRITER_NAME='/hdf5'
DEFAULT_HDF5_COMPARTMENTS = 'soma',

from . import logutil
log = logutil.Logger()

def vm_table_path(neuron, spine=None, comp=0):
    return '{}/Vm{}_{}{}'.format(DATA_NAME, neuron, '' if spine is None else spine, comp)

def find_vm_tables(neuron):
    return moose.wildcardFind('{}/Vm{}_#[TYPE=Table]'.format(DATA_NAME, neuron))

def setup_hdf5_output(model, neuron, filename=None, compartments=DEFAULT_HDF5_COMPARTMENTS):
    # Make sure /hdf5 exists
    if not moose.exists(HDF5WRITER_NAME):
        print('creating', HDF5WRITER_NAME)
        writer = moose.HDF5DataWriter(HDF5WRITER_NAME)
        #writer = moose.NSDFWriter(HDF5WRITER_NAME)
        writer.mode = 2 # Truncate existing file
        if filename is not None:
            writer.filename = filename
        moose.useClock(8, HDF5WRITER_NAME, 'process')
    else:
        print('using', HDF5WRITER_NAME)
        writer = moose.element(HDF5WRITER_NAME)

    for typenum,neur_type in enumerate(neuron.keys()):
        for ii,compname in enumerate(compartments):  #neur_comps):
            comp=moose.element(neur_type+'/'+compname)
            moose.connect(writer, 'requestOut', comp, 'getVm')

    if model.calYN:
        for typenum,neur_type in enumerate(neuron.keys()):
            for ii,compname in enumerate(compartments):  #neur_comps):
                comp=moose.element(neur_type+'/'+compname)
                for child in comp.children:
                    if child.className in {"CaConc", "ZombieCaConc"}:
                        cal = moose.element(comp.path+'/'+child.name)
                        moose.connect(writer, 'requestOut', cal, 'getCa')
                    elif  child.className == 'DifShell':
                        cal = moose.element(comp.path+'/'+child.name)
                        moose.connect(writer, 'requestOut', cal, 'getC')
    return writer

def wrap_hdf5(model, iterationName):
    import h5py as h5
    with h5.File(model.param_sim.fname, 'r+') as f:
        # Moose creates hdf5 groups at root level, corresponding to moose path.
        # Get the root level keys that are moose elements, move them under current
        # iteration level.
        f.create_group(iterationName)
        for k in f.keys():
            if moose.exists(k):
                f.move(k,iterationName+'/'+k)
        f.close()

def save_hdf5_attributes(model):
    import h5py as h5
    with h5.File(model.param_sim.fname, 'r+') as f:
        for k, v in vars(model.param_sim).items():
            f.attrs[k] = str(v)
        gitlog = util.gitlog(model)
        f.attrs['gitlog'] = gitlog
        f.attrs['Moose Version'] = moose.__version__
        f.close()


def write_textfile(tabset, tabname, fname, inj, simtime):
    time=np.linspace(0, simtime, len(tabset[list(tabset.keys())[0]][0].vector))
    header='time    '+'   '.join([t.neighbors['requestOut'][0].path for tab in tabset for t in tabset[tab]])
    outputdata=np.column_stack((time,np.column_stack([t.vector for tab in tabset for t in tabset[tab]])))
    new_fname=fname+'{0:.4g}'.format(inj)+tabname+'.txt'
    #f.write(header+'\n')
    np.savetxt(new_fname,outputdata,fmt='%.6f',header=header)
    return new_fname


def write_textfiles(model, inj):
        inj_nA=inj*1e9
        write_textfile(model.vmtab, 'Vm', model.param_sim.fname, inj_nA,
                              model.param_sim.simtime)
        if model.calYN:
            write_textfile(model.catab, 'Ca', model.param_sim.fname, inj_nA,
                                  model.param_sim.simtime)
        if model.spineYN and len(model.spinevmtab):
            write_textfile(list(model.spinevmtab.values()), 'SpVm',
                                  model.param_sim.fname, inj_nA, model.param_sim.simtime)
        if model.spineYN and len(model.spinecatab):
            write_textfile(list(model.spinecatab.values()), 'SpCa',
                                  model.param_sim.fname, inj_nA, model.param_sim.simtime)



def graphtables(model, neuron,pltcurr,curmsg, plas=[],compartments='all'):
    print("GRAPH TABLES, of ", neuron.keys(), "plas=",len(plas),"curr=",pltcurr)
    #tables for Vm and calcium in each compartment
    vmtab={}
    catab={key:[] for key in neuron.keys()}
    currtab={}

    # Make sure /data exists
    if not moose.exists(DATA_NAME):
        moose.Neutral(DATA_NAME)

    for typenum,neur_type in enumerate(neuron.keys()):
        if type(compartments)==str and compartments in {'all', '*'}:
                neur_comps = moose.wildcardFind(neur_type + '/#[TYPE=Compartment]')
        else:
            neur_comps=[moose.element(neur_type+'/'+comp) for comp in compartments]
        vmtab[neur_type] = [moose.Table(vm_table_path(neur_type, comp=ii)) for ii in range(len(neur_comps))]

        for ii,comp in enumerate(neur_comps):
            moose.connect(vmtab[neur_type][ii], 'requestOut', comp, 'getVm')

        if model.calYN:
            for ii,comp in enumerate(neur_comps):
                for child in comp.children:
                    if child.className in {"CaConc", "ZombieCaConc"}:
                        catab[neur_type].append(moose.Table(DATA_NAME+'/%s_%d_' % (neur_type,ii)+child.name))
                        cal = moose.element(comp.path+'/'+child.name)
                        moose.connect(catab[neur_type][-1], 'requestOut', cal, 'getCa')
                    elif  child.className == 'DifShell':
                        catab[neur_type].append(moose.Table(DATA_NAME+'/%s_%d_' % (neur_type,ii)+child.name))
                        cal = moose.element(comp.path+'/'+child.name)
                        moose.connect(catab[neur_type][-1], 'requestOut', cal, 'getC')

        if pltcurr:
            currtab[neur_type]={}
            #CHANNEL CURRENTS (Optional)
            for channame in model.Channels:
                tabs = [moose.Table(DATA_NAME+'/chan%s%s_%d' %(channame,neur_type,ii))
                        for ii in range(len(neur_comps))]
                currtab[neur_type][channame] = tabs
                for tab, comp in zip(tabs, neur_comps):
                    path = comp.path+'/'+channame
                    try:
                        chan=moose.element(path)
                        moose.connect(tab, 'requestOut', chan, curmsg)
                    except Exception:
                        log.debug('no channel {}', path)
    #
    # synaptic weight and plasticity (Optional) for one synapse per neuron
    plastab={key:[] for key in neuron.keys()}
    if len(plas):
        for num,neur_type in enumerate(plas.keys()):
            if len(plas[neur_type]):
                for comp_name in plas[neur_type]:
                    plastab[neur_type].append(add_one_table(DATA_NAME,plas[neur_type],comp_name))
    return vmtab,catab,plastab,currtab

def add_one_table(DATA_NAME, plas_entry, comp_name):
    if comp_name.find('/')==0:
       comp_name=comp_name[1:]
    plastab=moose.Table(DATA_NAME+'/plas' + comp_name)
    #plasCumtab=moose.Table(DATA_NAME+'/cum' + comp_name)
    syntab=moose.Table(DATA_NAME+'/syn' + comp_name)
    print(plas_entry)
    moose.connect(plastab, 'requestOut', plas_entry['plas'], 'getValue')
    #moose.connect(plasCumtab, 'requestOut', plas_entry['cum'], 'getValue')
    shname=plas_entry['syn'].path+'/SH'
    sh=moose.element(shname)
    moose.connect(syntab, 'requestOut',sh.synapse[0],'getWeight')
    return {'plas':plastab,
            #'cum':plasCumtab,
            'syn':syntab}

def create_desens_tabs(synchan,table_name,tabset):
    #print (' && cdt',synchan.path,end='')
    for neigh in synchan.neighbors['childOut']:
        if 'dep' in neigh.name or 'fac' in neigh.name:
            print(neigh.path)
            tabset.append((moose.Table(DATA_NAME+'/%s' %(table_name+neigh.name))))
            moose.connect(tabset[-1], 'requestOut', neigh, 'getValue')
    return

def syn_plastabs(connections, param_sim,plas=[]):
    if not moose.exists(DATA_NAME):
        moose.Neutral(DATA_NAME)
    #tables with synaptic conductance for all synapses that receive input
    syn_tabs={key:{} for key in connections.keys()}
    plas_tabs={key:{} for key in connections.keys()}
    #if model.desensYN
    desens_tabs={key:{} for key in connections.keys()}
    for neur_type in connections.keys():
        for neur_name in connections[neur_type].keys():
            if not len(syn_tabs[neur_type].keys()):
                syn_tabs[neur_type]={key:[] for key in list(connections[neur_type][neur_name].keys()) if key != 'postsoma_loc'}
            #if model.desensYN;
            if not len(desens_tabs[neur_type].keys()):
                desens_tabs[neur_type]={key:[] for key in list(connections[neur_type][neur_name].keys()) if key != 'postsoma_loc'}
            for syntype in list(syn_tabs[neur_type].keys()):
                for precomp in connections[neur_type][neur_name][syntype].keys():
                    if 'extern' in precomp:
                        for comp in connections[neur_type][neur_name][syntype][precomp].keys():
                            synchan=moose.element(neur_name+'/'+comp+'/'+syntype)
                            #print ('##### syn_plastabs',synchan.path,'/'+neur_name.split('/')[-1]+'-'+precomp,comp)
                            log.debug('{} {} {} {}', neur_name,syntype, precomp,synchan.path)
                            syn_tabs[neur_type][syntype].append(moose.Table(DATA_NAME+'/%s' %(neur_name.split('/')[-1]+'-'+precomp+CONNECT_SEPARATOR+comp.replace('/','-'))))
                            log.debug('{} {} ', syn_tabs[neur_type][syntype][-1], synchan)
                            moose.connect(syn_tabs[neur_type][syntype][-1], 'requestOut', synchan, 'getGk')
                            create_desens_tabs(synchan,syn_tabs[neur_type][syntype][-1].name,desens_tabs[neur_type][syntype])
                    else:
                        synchan=moose.element(neur_name+'/'+precomp.split(CONNECT_SEPARATOR)[-1]+'/'+syntype)
                        #print ('###########',synchan.path,'/'+neur_name.split('/')[-1]+'-'+precomp)
                        log.debug('{} {} {} {}', neur_name,syntype, precomp,synchan.path)
                        syn_tabs[neur_type][syntype].append(moose.Table(DATA_NAME+'/%s' %(neur_name.split('/')[-1]+'-'+precomp)))
                        log.debug('{} {} ', syn_tabs[neur_type][syntype][-1], synchan)
                        moose.connect(syn_tabs[neur_type][syntype][-1], 'requestOut', synchan, param_sim.plot_synapse_message)
                        create_desens_tabs(synchan,syn_tabs[neur_type][syntype][-1].name,desens_tabs[neur_type][syntype])
    #tables of dictionaries with instantaneous plasticity (plas), cumulative plasticity (plasCum) and synaptic weight (syn)
    if len(plas):
        for neur_type in plas.keys():
            for cell in plas[neur_type].keys():
                for syncomp in plas[neur_type][cell].keys():
                    plas_tabs.append(add_one_table(DATA_NAME, plas[neur_type][cell][syncomp], cell+syncomp))
    return syn_tabs, plas_tabs, desens_tabs

def spinetabs(model,neuron,comps='all'):
    if not moose.exists(DATA_NAME):
        moose.Neutral(DATA_NAME)
    #creates tables of calcium and vm for spines
    spcatab = defaultdict(list)
    spvmtab = defaultdict(list)
    for typenum,neurtype in enumerate(neuron.keys()):
        if type(comps)==str and comps in {'*', 'all'}:
            spineHeads=[moose.wildcardFind(neurtype+'/##/#head#[ISA=CompartmentBase]')]
        else:
            spineHeads=[moose.wildcardFind(neurtype+'/'+c+'/#head#[ISA=CompartmentBase]') for c in comps]
        for spinelist in spineHeads:
            for spinenum,spine in enumerate(spinelist):
                compname = spine.parent.name
                sp_num=spine.name.split(NAME_HEAD)[0]
                spvmtab[typenum].append(moose.Table(vm_table_path(neurtype, spine=sp_num, comp=compname)))
                log.debug('{} {} {}',spinenum, spine.path, spvmtab[typenum][-1].path)
                moose.connect(spvmtab[typenum][-1], 'requestOut', spine, 'getVm')
                if model.calYN:
                    for child in spine.children:
                        if child.className == "CaConc" or  child.className == "ZombieCaConc" :
                            spcatab[typenum].append(moose.Table(DATA_NAME+'/%s_%s%s'% (neurtype,sp_num,compname)+child.name))
                            spcal = moose.element(spine.path+'/'+child.name)
                            moose.connect(spcatab[typenum][-1], 'requestOut', spcal, 'getCa')
                        elif child.className == 'DifShell':
                            spcatab[typenum].append(moose.Table(DATA_NAME+'/%s_%s%s'% (neurtype,sp_num,compname)+child.name))
                            spcal = moose.element(spine.path+'/'+child.name)
                            moose.connect(spcatab[typenum][-1], 'requestOut', spcal, 'getC')
    return spcatab,spvmtab

def spiketables(neuron,param_cond):
    spiketab=[]
    for neur in neuron.keys():
        soma=moose.element(neur+'/'+param_cond.NAME_SOMA)
        spikegen=moose.SpikeGen(soma.path+'/spikegen')
        spikegen.threshold=0.0
        spikegen.refractT=1.0e-3
        msg=moose.connect(soma,'VmOut',spikegen,'Vm')
        spiketab.append(moose.Table('/data/spike_'+neur))
        moose.connect(spikegen,'spikeOut',spiketab[-1],'spike')
    return spiketab
