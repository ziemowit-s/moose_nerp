"""\
Function definitions for making populations of neurons

"""
from __future__ import print_function, division
import numpy as np
import moose

from spspine import logutil, util
log = logutil.Logger()

def count_neurons(netparams):
    size=np.ones(len(netparams.grid),dtype=np.int)
    length=np.ones(len(netparams.grid),dtype=np.float)
    numneurons=1
    volume=1
    for i in range(len(netparams.grid)):
	if netparams.grid[i]['inc']>0:
            length[i]=netparams.grid[i]['xyzmax']-netparams.grid[i]['xyzmin']
	    size[i]=np.int(length[i]/netparams.grid[i]['inc'])
	numneurons*=size[i]
        volume*=length[i]
    return size, numneurons, volume

def create_population(container, netparams):
    netpath = container.path
    proto=[]
    neurXclass={}
    neurons=[]
    #determine total number of neurons
    size,numneurons,vol=count_neurons(netparams)
    #array of random numbers that will be used to select neuron type
    rannum = np.random.uniform(0,1,numneurons)
    pop_percent=[]
    for neurtype in netparams.pop_dict.keys():
        proto.append(moose.element(neurtype))
        neurXclass[neurtype]=[]
        pop_percent.append(netparams.pop_dict[neurtype].percent)
        #create cumulative array of probabilities for selecting neuron type
    choicearray=np.cumsum(pop_percent)
    #Error check for last element in choicearray equal to 1.0
    log.info("numneurons= {} {} choicarray={} rannum={}", size, numneurons, choicearray, rannum)
    for i,xloc in enumerate(np.linspace(netparams.grid[0]['xyzmin'], netparams.grid[0]['xyzmax'], size[0])):
        for j,yloc in enumerate(np.linspace(netparams.grid[1]['xyzmin'], netparams.grid[1]['xyzmax'], size[1])):
	    for k,zloc in enumerate(np.linspace(netparams.grid[2]['xyzmin'], netparams.grid[2]['xyzmax'], size[2])):
                #for each location in grid, assign neuron type, update soma location, add in spike generator
		neurnumber=i*size[2]*size[1]+j*size[2]+k
		neurtypenum=np.min(np.where(rannum[neurnumber]<choicearray))
                log.info("i,j,k {} {} {} neurnumber {} type {}", i,j,k, neurnumber, neurtypenum)
		typename = proto[neurtypenum].name
		tag = '{}_{}'.format(typename, neurnumber)
		neurons.append(moose.copy(proto[neurtypenum],netpath, tag))
		neurXclass[typename].append(container.path + '/' + tag)
		comp=moose.Compartment(neurons[neurnumber].path + '/soma')
		comp.x=i*xloc
		comp.y=j*yloc
		comp.z=k*zloc
		log.debug("x,ymz={},{},{} {}", comp.x, comp.y, comp.z, neurons[neurnumber].path)
		#spike generator - can this be done to the neuron prototype?
		spikegen = moose.SpikeGen(comp.path + '/spikegen')
                #should these be parameters in netparams?
		spikegen.threshold = 0.0
		spikegen.refractT=1e-3
		m = moose.connect(comp, 'VmOut', spikegen, 'Vm')
    return {'cells': neurons,
            'pop':neurXclass}

