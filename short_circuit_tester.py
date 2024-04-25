import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping, READ_ALL_AVAILABLE
import numpy as np
import time
from datetime import datetime
import matplotlib.pyplot as plt

class ShortCircuitTester:
    def __init__(self, datarate, short_time, pyro_current_threshold, test_name):
        self.test_name = test_name
        self.cDAQ_name = 'cDAQ9184-186A96E'
        self.datarate = datarate                     #datarate in Hz of logging
        self.samples_before_buffer = 1000        #number of samples to be captured in buffer before grabbing from device
        self.pre_log_time = 0.75                 #duration of pre-short log time, seconds
        self.delay_before_SCR = 0.25            #time between closing contactor and activating SCR
        self.short_time = short_time                  #duration of short circuit, seconds
        self.scr_pulse_time = 0.1                #duration of SCR pulse, seconds
        self.pyro_pulse_time = 0.2                #duration of pyro pulse, seconds
        self.pyro_evaluation_time = 0.500              #duration after short should have ended (contactor open) to blow pyro, if current threshhold exceeded
        self.post_log_time = 1.0                 #duration of post-short log time, seconds
        self.pyro_current_threshold = pyro_current_threshold       #current in A that trigger pyro to blow, when evaluated after pyro_fire_time
        self.contactor_task = nidaqmx.Task('contactor')
        self.scr_task = nidaqmx.Task('scr')
        self.pyro_task = nidaqmx.Task('pyro')
        self.light_task = nidaqmx.Task('light')
        self.analog_task = nidaqmx.Task('analog_inputs')
        self.volt_scale = 10
        self.shunt_resistance = 0.0001  #ohms
        self.data_volt = []
        self.data_current = []
        self.data_time = []
        #self.reset_cDAQ()
        self.initialize_outputs()
        self.initialize_inputs()

    def reset_cDAQ(self):
        nidaqmx.system.device.Device(self.cDAQ_name).reset_device()
        print('resetting cDAQ')
        time.sleep(2)

    def initialize_outputs(self):
        self.contactor_task.do_channels.add_do_chan(f"{self.cDAQ_name}Mod2/line0", line_grouping=LineGrouping.CHAN_PER_LINE)
        self.contactor_task.write(False, auto_start=True)

        self.scr_task.do_channels.add_do_chan(f"{self.cDAQ_name}Mod2/line1", line_grouping=LineGrouping.CHAN_PER_LINE)
        self.scr_task.write(False, auto_start=True)

        self.pyro_task.do_channels.add_do_chan(f"{self.cDAQ_name}Mod2/line2", line_grouping=LineGrouping.CHAN_PER_LINE)
        self.pyro_task.write(False, auto_start=True)

        self.light_task.do_channels.add_do_chan(f"{self.cDAQ_name}Mod2/line3", line_grouping=LineGrouping.CHAN_PER_LINE)
        self.light_task.write(False, auto_start=True)
    
    def disable_outputs(self):
        self.contactor_task.write(False)
        self.contactor_task.close()
        self.scr_task.write(False)
        self.scr_task.close()
        self.pyro_task.write(False)
        self.pyro_task.close()
        self.light_task.write(False)
        self.light_task.close()

    def close_contactor(self):
        self.contactor_task.write(True)

    def open_contactor(self):
        self.contactor_task.write(False)
    
    def pulse_scr(self):
        self.scr_task.write(True)
        time.sleep(self.scr_pulse_time)
        self.scr_task.write(False)
    
    def fire_pyro(self):
        self.pyro_task.write(True)
        time.sleep(self.pyro_pulse_time)
        self.pyro_task.write(False)

    def light_on(self):
        self.light_task.write(True)

    def light_off(self):
        self.light_task.write(False)

    def check_to_fire_pyro(self):
        last_currents = self.data_current[-100:]     #last 100 current measurements
        avg_current = sum(last_currents) / len(last_currents)
        if abs(avg_current) > self.pyro_current_threshold:
            self.fire_pyro()
            return f'pyro fired at current of {avg_current} A'
        else:
            return f'pyro NOT fired at current of {avg_current} A'

    def initialize_inputs(self):
        self.analog_task.ai_channels.add_ai_voltage_chan(f"{self.cDAQ_name}Mod1/ai0")
        self.analog_task.ai_channels.add_ai_voltage_chan(f"{self.cDAQ_name}Mod1/ai1")
        self.analog_task.timing.cfg_samp_clk_timing(self.datarate, sample_mode=AcquisitionType.CONTINUOUS)
        self.analog_task.register_every_n_samples_acquired_into_buffer_event(self.samples_before_buffer, self.callback)
    
    def callback(self, task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        self.append_data(self.samples_before_buffer)
        return 0
    
    def append_data(self, points):
        buffer = self.analog_task.read(number_of_samples_per_channel=points)
        self.data_volt.extend(np.multiply(buffer[0], self.volt_scale))
        self.data_current.extend(np.divide(buffer[1], self.shunt_resistance))
    
    def start_measuring(self):
        self.analog_task.start()

    def stop_measuring(self):
        self.append_data(READ_ALL_AVAILABLE)
        self.analog_task.stop()
        self.data_time = np.arange(len(self.data_volt)) / self.datarate
        time_offset = self.pre_log_time + self.delay_before_SCR
        self.data_time = np.subtract(self.data_time, time_offset)   #shift time vector so t=0 is start of short

    def save_data(self):
        data_array = np.asarray([self.data_time, self.data_volt, self.data_current]).transpose()
        filename = 'logs/' + self.test_name + '-' + datetime.now().strftime("%m_%d_%Y-%H_%M_%S") + '.csv'
        header = 'Time (s),Battery Voltage (V),Current (A)'
        np.savetxt(filename, data_array, delimiter=',', header=header, fmt='%0.5f')
    
    def plot(self):
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
        ax1.plot(self.data_time, self.data_volt)
        ax2.plot(self.data_time, self.data_current)
        fig.suptitle(f"Short Circuit - {self.test_name}")
        plt.xlabel("Time (s)")
        ax1.set(ylabel='Battery Voltage (V)')
        ax2.set(ylabel='Current (A)')
        plt.show()

    def start_countdown(self):
        input('press enter to start countdown')
        print('-----short circuit test initiated - press ctrl-c to abort------')
        for i in range(5, 0, -1):
            print(i)
            time.sleep(1)

    def run_test(self):
        self.start_countdown()
        self.light_on()
        self.start_measuring()
        print(f'measurement started at {self.datarate} Hz')
        print(f'wait for {self.pre_log_time} seconds (pre-logging)')
        time.sleep(self.pre_log_time)
        self.close_contactor()
        print('contactor closed')
        print(f'wait for {self.delay_before_SCR} seconds (delay after closing contactor)')
        time.sleep(self.delay_before_SCR)
        self.pulse_scr()
        print('SCR activated')
        print(f'shorting for {self.short_time} seconds')
        time.sleep(self.short_time)
        self.open_contactor()
        print('contactor opened')
        print(f'wait for {self.pyro_evaluation_time} seconds (delay for evaluating pyro)')
        time.sleep(self.pyro_evaluation_time)
        pyro_result = self.check_to_fire_pyro()
        print(pyro_result)
        print(f'wait for {self.post_log_time} seconds (post-logging)')
        time.sleep(self.post_log_time)
        self.stop_measuring()
        print(f'measurement stopped - {len(self.data_time)} data points recorded')
        max_current = max(self.data_current)
        print(f'test completed - max current = {max_current} A')
        self.light_off()
        self.disable_outputs()
