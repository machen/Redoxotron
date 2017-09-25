import visa
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""TO DO LIST:
1) With the readings 0.000904, 0.000904, 0.000903, 0.000905, 0.000904 gets 0.000703 as average
2) Enable variable timing
3) Prevent and log errors encountered by multimeter during run
4) Catch KeyboardInterrupt in main loop and close resource on interrupt
5) Clean up code
"""

# note:  Power-cycle keithley prior to re-starting long experiment...
# Run this program as root (sudo idle3) or it probably won't work!


def takeMeasurement(device, measNum, nMeas, pauseLen, printVal=True,
                    measType="voltage:dc"):
    measurements = np.empty(nMeas, dtype=float)
    measTime = time.asctime(time.localtime(time.time()))
    print('\n'+measType+' measurement number: {:d}'.format(measNum))
    print('Measurement time: {:s}'.format(measTime))
    print('Starting {:s} measurements').format(measType)
    for i in range(nMeas):
        # Try to format and append the current measurement, continue otherwise
        try:
            currMeas = device.query("measure:{}?".format(measType))
            currMeas = currMeas.strip()  # Does this work??
            currMeas = float(currMeas)
            measurements[i] = currMeas
            if printVal:
                print("Reading#:{:d}: {:f}".format(i, currMeas))
        except ValueError:
            print("Non-float value returned. No data recorded.")
            measurements[i] = np.nan
            continue
        except:
            print("Exception: Instrument Read problem.",
                  "No data recorded. Do you have the right command?")
            measurements[i] = np.nan
            continue
        finally:
            time.sleep(pauseLen)
    realMeas = measurements[~np.isnan(measurements)]  # Strip out error Nan
    [measAvg, measStd, measSize] = [np.mean(realMeas), np.std(realMeas),
                                    len(realMeas)]
    print("\n Average: {:f}, standard dev: {:f}, number of measurements: {:d}"
          .format(measAvg, measStd, measSize))
    return measTime, [measAvg, measStd, measSize]


rm = visa.ResourceManager('@py')
print(rm.list_resources())
keithley = rm.open_resource('USB0::1510::8448::8004460::0::INSTR')
keithley.write('*cls')
time.sleep(1)
keithley.write('*rst')
time.sleep(1)

""" USER DEFINED INPUTS GO HERE """
plotvolt = True  # Plot voltage data in real-time?
loopvals = True  # print measurements in loop

""" Choose measurements (set to True to enable measurement).
    Note that the multimeter must be set up to take said measurements!"""

nMeasureTypes = 1
resMeas = False
currentMeas = False
voltageMeas = True

countdown_timer = 5  # Sets interval for announcing next measurement

totaltime = 3600  # Experimental time length in seconds, more time->longer run.
tCycles = 15  # Time in seconds between measurements
numpoints = 5  # Number of measurements to average at each point
# Seconds between measurements. Stability requries 0.05 sec or greater.
pauseMeasure = 0.2


""" Estimates the time measurements should take, and exits if the estimate
    is larger than the time between measurements (tCycles) """

estMeasTime = ((pauseMeasure+1.25)
               * nMeasureTypes * numpoints)+6  # Multiplied by 3 = fudge factor
print("data collection time is guessed to be %d seconds,",
      " time between datapoints is %d seconds" % (estMeasTime, tCycles))
if tCycles >= estMeasTime:
    print("data collection scheme ok, starting in 5 seconds")
    time.sleep(5)

else:
    print("not enough time to collect %d measurments",
          "between %d second intervals \n" % (numpoints, tCycles))
    print("increase seconds between measurements",
          " or lower number of replicates per point \n")
    print("closing in 5 seconds....")
    time.sleep(5)
    print("Exiting with error. goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()


""" USER NON-SERVICABLE PARTS """

floattime = time.time()
initialtime = time.time()
"""Data is stored as a dataframe, with an DateTime index corresponding
to when the measurement was taken. Script tries to open previously
collected data first."""
try:
    data = pd.read_csv('data.csv')
except FileNotFoundError:
    data = pd.DataFrame(columns=["Avg", "StdDev", "nMeas", "Type"])
time.sleep(2)
print("initial test measurement...")

voltage = keithley.query("measure:voltage:dc?")
if voltage == "":
    print("problem with Keithley. Stopping program in 5 seconds. ")
    print("power cycle Keithly and re-start program")
    time.sleep(5)
    print("Exiting with error. goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()

print("equipment ok, starting data collection\n")
time.sleep(2)

print("starting initial measurement\n")
time.sleep(1)


measureNum = 0  # Marker for the measurement you're on

# Declare plotting variables

plotInitialTime = time.time()
xvals = ([0])
yvals = ([0])
stderrlist = ([0])
xmin = ([0])
ymin = ([0])
ymax = ([0])

plt.ion()  # Turns matplotlib interactive mode on.

while True:
    # Initialize times
    if measureNum == 0 or time.time() >= floattime:
        floattime = time.time()+tCycles
        currtime = time.asctime(time.localtime(time.time()))
        currtimeplain = time.time()

        if voltageMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=loopvals,
                                          measType="voltage:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("voltage:dc")
            time.sleep(2)
        if currentMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=loopvals,
                                          measType="current:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("current:dc")
            time.sleep(2)
        if resMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=loopvals,
                                          measType="resistance")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("resistance")
            time.sleep(2)
        measureNum += 1
        print("\n\n\nwriting data to file...")
        data.to_csv('data.csv')
        print("done writing to file...")
        thisround=((time.time())-currtimeplain)
        print("all measurements required a total of %f seconds\n"%thisround)
        newround = (floattime-(time.time()))
        print("%d seconds until next round of measurements"%newround)
        countdown= newround-countdown_timer

        ##plot voltage values as they come in

        if plotvolt==True:
            plottime=(time.time())-(plotInitialTime)
            xvals.append(plottime)
            yvals.append(voltage_average)
            stderrlist.append(voltage_sd)


            xmin=min(xvals); xmax = max(xvals)
            ymin=(min(yvals)-((max(stderrlist))*2)); ymax = (max(yvals)+((max(stderrlist))*2))
            axes = plt.gca()
            axes.set_xlim([xmin, xmax])
            axes.set_ylim([ymin, ymax])
            plt.errorbar(xvals, yvals, yerr=stderrlist, fmt='o')
            plt.pause(0.05)

            
        
    

    elif time.time()>=initialtime+totaltime:
        break

    elif floattime-time.time()<=countdown:
        endtime=(initialtime+totaltime)-(time.time())
        print ("%d seconds before next measurement, and %d seconds before end of experiment"%(countdown, endtime))
        countdown-=countdown_timer

print ("elapsed time: %f seconds"%(floattime-initialtime))
print("normal exit. goodbye....")
keithley.write('system:local')
keithley.close()

while True:
    plt.pause(0.05)
        



