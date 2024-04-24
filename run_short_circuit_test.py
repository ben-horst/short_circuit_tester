from short_circuit_tester import ShortCircuitTester
import time
import matplotlib.pyplot as plt
import numpy as np

#-------------user input------------------
datarate = 10000                     #datarate in Hz of logging
short_time = 2                       #duration of short circuit, seconds
pyro_current_threshold = 20.0        #current in A that trigger pyro to blow, when evaluated after pyro_fire_time
#-------------user input------------------


tester = ShortCircuitTester(datarate, short_time, pyro_current_threshold)
tester.run_test()
tester.save_data()
tester.plot()
