from moose_nerp.prototypes.inject_func import ParadigmParams, StimParams, StimLocParams

example_pulse_seqeunce = {1: [0, 1], 2: [2, 3], 3: [0, 1]}

# UNITS: frequency (f_pulse,f_burst,f_train) in Hz; width_AP, AP_interval, and ISI : sec; A_inject: Amps, n (n_pulse,n_burst,n_train,n_AP) dimensionless
AP_1 = ParadigmParams(f_pulse=50., n_pulse=1, A_inject=1e-9, f_burst=1, n_burst=1, f_train=1, n_train=1, width_AP=0.005,
                      AP_interval=0.01, n_AP=1, ISI=-0.040, name="1_AP")
PSP_1 = ParadigmParams(f_pulse=1., n_pulse=1, A_inject=1e-9, f_burst=1, n_burst=1, f_train=1, n_train=1, width_AP=0.005,
                       AP_interval=0.01, n_AP=0, ISI=0, name="1_PSP")

PSP_20_Hz = ParadigmParams(f_pulse=20., n_pulse=20, A_inject=0, f_burst=1, n_burst=1, f_train=1, n_train=1,
                           width_AP=0.005, AP_interval=0.01, n_AP=0, ISI=0, name="20_Hz")

PSP_100_Hz = ParadigmParams(f_pulse=100., n_pulse=100, A_inject=0, f_burst=1, n_burst=1, f_train=1, n_train=1,
                            width_AP=0.005, AP_interval=0.01, n_AP=0, ISI=0, name="100_Hz")

TBS = ParadigmParams(f_pulse=50., n_pulse=4, A_inject=0, f_burst=8, n_burst=10, f_train=0.1, n_train=1, width_AP=1.1,
                     AP_interval=2., n_AP=1, ISI=0, name="TBS")

TestPlas = ParadigmParams(f_pulse=5, n_pulse=3, A_inject=0, f_burst=1, n_burst=1, f_train=1, n_train=1, width_AP=0.005,
                          AP_interval=0.01, n_AP=0, ISI=0, name="TestPlas")

inject = ParadigmParams(f_pulse=5, n_pulse=0, A_inject=0.25e-9, f_burst=1, n_burst=1, f_train=1, n_train=1,
                        width_AP=0.005, AP_interval=0.01, n_AP=0, ISI=0, name="inject")

# This list is required to assign different stim paradigms if specified by the arg_parser
paradigm_dict = {'inject': inject,
                 'TBS': TBS,
                 'TestPlas': TestPlas,
                 'AP_1': AP_1,
                 'PSP_1': PSP_1,
                 'PSP_20_Hz': PSP_20_Hz,
                 'PSP_100_Hz': PSP_100_Hz}

# stim_dendrite list must correspond to dendrites in morphology.p
# spine_density units: fraction of spines connected in specified compartments
location = StimLocParams(which_spines='all', spine_density=0.2, pulse_sequence=None, stim_dendrites=['31_4'])

# stim_delay units: sec
Stimulation = StimParams(Paradigm=inject, stim_delay=0.02, StimLoc=location)

# pulse sequence should be of the form:
# {1:[0,1],2:[2,3],3:[0,1]} -- for each pulse specify a list of spines to stimulate
