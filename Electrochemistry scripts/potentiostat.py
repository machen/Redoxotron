import sys
import serial
import io
# from serial.tools import list_ports
import time
import numpy as np
import struct
from struct import *
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", ".*GUI is implemented.*")

"""Intial version of script was off of Ben Kocar V2.6 of potentiostat
script, taken 10/27/2017"""


def open_port(ser):
    try:
        if ser.is_open is True:
            ser.close()
        if ser.is_open is False:
            # Open serial port. may need to change port value
            print("opening port\n")
            ser = serial.Serial('/dev/ttyACM0', rtscts=True, timeout=3)
            time.sleep(0.5)
            testread = ser.read(10)
            time.sleep(1)
            testread2 = ser.read(10)
            if testread is not testread2 and testread2 is not '':
                print("AMC0 sucessfully opened, but device may still be",
                      " collecting data from previous run...sending abort",
                      " command and i/o flush")
                abort_potentiostat(ser)
                time.sleep(0.5)
                checkser = ser.is_open
                if checkser is True:
                    print("buffer erase seemed to work",
                          "...continuing to data collection")
                    return ser
            else:

                print("AMC0 succesfully opened.",
                      " writing experimental parameters")
                write_params(ser)
                return ser
        else:
            print("port already open...")
    except:
        print("could not open port on AMC0, trying AMC1....")
        alt_port(ser)


def alt_port(ser):
    try:
        if ser.is_open is True:
            ser.close()
        if ser.is_open is False:
            # Open serial port. may need to change port value
            print("opening port\n")
            ser = serial.Serial('/dev/ttyACM1', rtscts=True, timeout=3)
            time.sleep(3)
            testread = ser.read(10)
            time.sleep(1)
            testread2 = ser.read(10)
            if testread is not testread2 and testread2 is not '':
                print("AMC1 sucessfully opened, but device may still be",
                      " collecting data from previous run...sending abort",
                      " command and i/o flush")
                abort_potentiostat(ser)
                time.sleep(0.5)
                checkser = ser.is_open
                if checkser:
                    print("buffer erase seemed to work...",
                          "continuing to data collection")
                    return ser
            else:
                print("AMC1 succesfully opened. ",
                      "Writing experimental parameters")
                write_params(ser)
                return ser
        else:
            print("port already open...")
    except:
        print("\ncould not open AMC1, retrying AMC0 (2nd attempt)",
              " and staying in loop....\n")
        if ser.is_open is True:
            ser.close()
        open_port()
        time.sleep(1)

def write_params(ser):
        dac_mV = int(21846*(ex_mV/1000)+32768)
        ser.write(b'!0\n')
        time.sleep(1)
        ser.write(b'V\n')
        time.sleep(1)
        ser.write(b'!10\n')
        time.sleep(1)
        ser.write(b'EA%d 03 1 \n' % adc_gain)
        time.sleep(1)  # If changing gain, check number of characters to send
        ser.write(b'!6\n')
        time.sleep(1)
        ser.write(b'EG%d 0 \n' % ex_dac_gain)
        time.sleep(1)
        ser.write(b'!6\n')
        time.sleep(1)
        ser.write(b'ER1 0\n')
        time.sleep(1)
        ser.write(b'%d\n' % dac_mV)
        time.sleep(1)
        ser.write(b'%d\n' % ex_time)
        time.sleep(1)
        print("\nParameters successfully uploaded....")
        if ser.is_open is True:
            print("port still open after writing params,",
                  " continuing to data collection loop...\n")
        return ser


def abort_potentiostat(ser):      # Aborts data collection without closing port
        time.sleep(0.5)
        ser.write(b'!1\n')
        time.sleep(1)
        ser.write(b'a\n')
        time.sleep(1)
        count = 0
        for i in range(20):
            data = ser.read(100)
            # Print(data)
            if b'#' in data:
                print("Potentiostat program successfully aborted,",
                      " flushing i/o buffer")
                time.sleep(2)
                ser.flushOutput()
                ser.flushInput()
                time.sleep(1)
                print("sending experimental parameters to potentiostat")
                write_params(ser)
                return ser
            else:
                print("Waiting for potentiostat to stop measurement.",
                      " Timeout after 25 datapoints. Current iter: %d" % i)
                time.sleep(1)

        print("timeout for abort command, trying again")
        count += 1
        if count == 10:
            print("number of abort attempts greater than 10,",
                  " attempting port reset")
            open_port(ser)
        abort_potentiostat(ser)


def data_collection(loopnumber, start_time, ser, refresh_time, looptime,
                    exptime, collection_countdown):
    timeold = 0
    currsum = []
    global xvals
    global yvals
    global stderrlist
    try:
        for line in ser:
            time_now = time.time()
            data = ser.read(10)
            if data.startswith(b'B'):
                # note: Dstat returns data in binary as hexadecimal,
                # form \xhh (where hh = 2-value hex)
                # parse data read from dstat
                x = data.replace(b'B\n', b'')
                new = struct.unpack('<HHl', x)
                sec, millisec, curr = new
                float(sec)
                float(millisec)
                float(curr)
                exptime = (sec+(millisec/1000.))
                current = (curr)*(adc_gain/2)*(1.5/gain/8388607)
                currsum.append(current)
            if time_now >= collection_countdown and data.startswith(b'B'):
                # Track time and update data matrix when experimental time exceeds specified timeloop
                    exptime_int = int(exptime)

                    if exptime_int is not 0:

                        print("\n%d seconds reached in data collection loop.",
                              " recording averages from data point %d"
                              % (exptime, loopnumber))
                        if exptime < (avg_time/2):
                            time_average_exp = time_now
                        else:
                            time_average_exp = (time_now-(avg_time/2))

                        mean_current = np.mean(currsum)
                        sd_current = np.std(currsum)
                        tpointsa = len(currsum)
                        print("time:", time_average_exp)
                        print("current:", mean_current)
                        print("standard_deviation:", sd_current)
                        print("number of points:", tpointsa)
                        z = [(time_average_exp),
                             (mean_current),
                             (sd_current),
                             (tpointsa)]

                        # write data to file
                        print("writing data to file\n")
                        f = open('test.dat', 'a')
                        f.write('\n')
                        f.write(str(z))
                        f.close

                        # update plot

                        if loopnumber == 1:

                            plot_time = (time_average_exp-start_time)
                            xvals = [(plot_time)]
                            yvals = [(mean_current)]
                            stderrlist = [(sd_current)]

                        else:
                            plot_time = (time_average_exp-start_time)
                            xvals.append(plot_time)
                            yvals.append(mean_current)
                            stderrlist.append(sd_current)

                            xmin = min(xvals)
                            xmax = max(xvals)
                            ymin = min(yvals)
                            ymax = max(yvals)
                            axes = plt.gca()
                            axes.set_xlim([xmin, xmax])
                            axes.set_ylim([ymin, ymax])
                            plt.errorbar(xvals, yvals, yerr=stderrlist, color='g', fmt='--o')
                            plt.pause(0.1)

                        currsum = []
                        collection_countdown = time_now+avg_time
                        loopnumber += 1
            if time_now >= looptime:


                # potentiostat refresh when "refresh frequncy" exceeded by timeloop

                print("\npotentiostat refresh, breaking data collection loop")
                time.sleep(1)
                if loopnumber == "":
                    loopnumber = 1
                return(loopnumber, ser)
            difftimes = time_now-timeold
            if difftimes >= countdownint:
                timeleft = collection_countdown-time_now

                if timeleft > 0:
                    print("recording time-averaged data in %d seconds" % timeleft)
                    timeold = time_now

    except:
        print("\nproblem with data collection loop. Will attempt to reset potentiostat\n")
        if ser.is_open is True:
            ser.close()

        if loopnumber is "":
            loopnumber = 1
        if ser == "":
            ser = serial.Serial('/dev/ttyACM0', timeout=3)

        print("/nloopnumber, ser:/n", loopnumber, ser)
        time.sleep(5)
        return(loopnumber, ser)


def main():
    pot_refresh_time = 0.
    exptime = 0
    refresh_time = avg_time
    ser = serial.Serial(port=None)
    time_average = 0
    time_average_exp = 0
    start_time = time.time()
    time_now = time.time()
    collection_countdown = time_now+avg_time
    loopnumber = 1
    refresh_time = time_now+refresh_freq
    f = open('test.dat', 'a')
    f.write('\n\n\ndate,exp name, mV, dac_gain value, actual dac gain, adc_gain, adc_gain_trim, ex_time, avg_time, refresh_freq\n')
    f.write('%s,%s, %d, %d, %d, %d, %d, %d, %d, %d'%(time_now,exp_name,ex_mV,ex_dac_gain,gain,adc_gain,gain_trim,ex_time,avg_time,refresh_freq))
    f.write('\n\n\nStart run.......     time-curr-sd-points     ###########################################################')
    f.close

    init_flag = 0
    while True:

        try:

            if use_port_refresh is False and use_abort is False and init_flag == 0:
                name = input("no refresh mechanism specified....are you sure you want to proceed? y/n")
                init_flag = 1
                if name != 'y':
                    print("closing port and exiting")
                    if ser.is_open==True:
                        ser.close()
                    sys.exit()
            if ser.is_open is False:
                ser = open_port(ser)
                time.sleep(0.5)
            if use_abort is True:
                print("refreshing potentiostat without closing port")
                abort_potentiostat(ser)
                time.sleep(0.1)

            time_now = time.time()
            looptime = time_now+refresh_freq
            loopnumber, ser = data_collection(loopnumber, start_time, ser,
                                              refresh_time, looptime,
                                              exptime, collection_countdown)
            if use_port_refresh is True:
                print("refreshing potentiostat through port reset")
                print("closing port")
                ser.close()
                time.sleep(5)
        except:
            print("problem in main program loop. attempting to clear variables and reset")
            if ser.is_open is True:
                ser.close()
            time.sleep(5)
            pot_refresh_time = 0.
            exptime = 0
            refresh_time = avg_time
            ser = serial.Serial(port=None)
            time_average = 0
            time_average_exp = 0
            start_time = time.time()
            time_now = time.time()
            collection_countdown = time_now+avg_time
            loopnumber = 1
            refresh_time = time_now+refresh_freq
            print("reset complete...trying again")
            time.sleep(2)
            pass

# name of experiment
exp_name = 'test'


# GLOBAL VARIABLES: CHANGE ME

#interval over which data is averaged
avg_time = 60 ## 600 = 10 min


#potentiostat voltage (mV)
ex_mV = -800

# dac gains: change this if current sensitivity to change is to high or too low as a function of resistance. 1 or 2 are good "general" numbers to start with. May see little change in current with large change in resistance at setting of "0"

ex_dac_gain = 1. ## set dac gain here. gain value of 2 is EG2, gain of 1 is EG1, etc
gain = 100 #!!!!Set this according to the table below (and value chosen for ex_dac_gain). e.g. "2" = 3k (set to 1 for zero ohms to avid division arrors)

            # gains allowed by dstat. use lowest value to detect (desired) differences in current
            #define POT_GAIN_0 0
            #define POT_GAIN_100 1
            #define POT_GAIN_3k 2
            #define POT_GAIN_30k 3
            #define POT_GAIN_300k 4
            #define POT_GAIN_3M 5
            #define POT_GAIN_30M 6
            #define POT_GAIN_100M 7




# generally DO NOT need to change these
adc_gain = 2  # this is generally held at 2
gain_trim = 0  # leave at 0 for now

# only change these if experiment end is desired
ex_time = 25200  # length of run. set to value greater than refresh_freq for running infinite loop...25200 = 7 hours
refresh_freq = 600  # potentiostat refresh frequency in seconds 3600=1 hr, 14400 = 4 hours

# countdown interval

countdownint=10


# close port with refresh. set "true" if abort attempt is coupled with port closure

use_port_refresh = True
use_abort = True

# Plotting axis global vars
xvals = [()]
yvals = [()]
stderrlist = [()]

if __name__ == "__main__":
    main()
