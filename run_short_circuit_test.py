from short_circuit_tester import ShortCircuitTester
import time
import matplotlib.pyplot as plt
import numpy as np

#-------------user input------------------
datarate = 10000                     #datarate in Hz of logging
short_time = 0.25                       #duration of short circuit, seconds
pyro_current_threshold = 20.0        #current in A that trigger pyro to blow, when evaluated after pyro_fire_time
test_name = 'droid_hardshort'         #name included in plot title and logfile
#-------------user input------------------


tester = ShortCircuitTester(datarate, short_time, pyro_current_threshold, test_name)
tester.run_test()
tester.save_data()
tester.plot()
