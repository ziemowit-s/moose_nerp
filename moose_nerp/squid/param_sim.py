import logging
from argparse import Namespace

from .param_cond import NAME_SOMA

param_sim = Namespace()

# Options for setting up stim paradigm
param_sim.stim_loc = NAME_SOMA
param_sim.stim_paradigm = 'inject'
param_sim.injection_current = [1e-9]
param_sim.injection_delay = 200e-3
param_sim.injection_width = 60e-3
param_sim.simtime = 30e-3

param_sim.neuron_type = None

param_sim.logging_level = logging.WARNING

param_sim.save = False  # True # save to hdf5
param_sim.save_txt = False  # True # Save text files

param_sim.simdt = 1e-05
param_sim.hsolve = True

param_sim.plotcomps = [NAME_SOMA]

param_sim.fname = None  # `None` uses default specified by stim paradigm

param_sim.plot_vm = True
param_sim.plotdt = 0.0002

param_sim.plot_activation = False  # None
param_sim.plot_calcium = False  # True #True
param_sim.plot_channels = False  # 0
param_sim.plot_current = False  # None
param_sim.plot_current_label = 'Cond, S'
param_sim.plot_current_message = 'getGk'
param_sim.plot_netvm = False  # None
param_sim.plot_network = False  # None
param_sim.plot_synapse = False  # None
param_sim.plot_synapse_label = 'Cond, nS'
param_sim.plot_synapse_message = 'getGk'
