import visa
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""
TO DO LIST:
1) Enable variable timing
2) Prevent and log errors encountered by multimeter during run. LINE 123
3) Catch KeyboardInterrupt in main loop and close resource on interrupt
4) Update CSV output to capture seconds place in times
"""

# note:  Power-cycle keithley prior to re-starting long experiment...
# Run this program as root (sudo idle3) or it probably won't work!


def takeMeasurement(device, measNum, nMeas, pauseLen, printVal=True,
                    measType="voltage:dc"):
    measurements = np.empty(nMeas, dtype=float)
    measTime = time.asctime(time.localtime(time.time()))
    print('\n'+measType+' measurement number: {:d}'.format(measNum))
    print('Measurement time: {}'.format(measTime))
    print('Starting {} measurements'.format(measType))
    for i in range(nMeas):
        # Try to format and append the current measurement
        try:
            currMeas = device.query("measure:{}?".format(measType))
            currMeas = currMeas.strip()
            currMeas = float(currMeas)
            measurements[i] = currMeas
            if printVal:
                print("Reading #{:d}: {:e}".format(i, currMeas))
        # In the case of an error, write value as NaN
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
    # Remove NaN values generated by errors, then calculate avg and stddev
    realMeas = measurements[~np.isnan(measurements)]
    [measAvg, measStd, measSize] = [np.mean(realMeas), np.std(realMeas),
                                    len(realMeas)]
    print("\nAverage: {:0.2e}, Std Dev: {:0.2e}, No. of Measurements: {:d}"
          .format(measAvg, measStd, measSize))
    return measTime, [measAvg, measStd, measSize]


""" USER DEFINED INPUTS GO HERE """

plotVolt = True  # Plot voltage data in real-time?
printVals = True  # print measurements in loop

""" Choose measurements (set to True to enable measurement).
    Note that the multimeter must be set up to take said measurements!"""

nMeasureTypes = 1
resMeas = False
currentMeas = False
voltageMeas = True

countdownTime = 60  # Sets interval for announcing next measurement

expTimeLength = 12*60*60  # Script run time in seconds
# Specify an array with initial times as an iterable
initialTCycle = np.concatenate([np.ones(20)*120, np.ones(20)*300])
finalTCycle = 30*60  # Final time interval in seconds
tCycles = iter(initialTCycle)  # Iterable with the time between samples
nMeas = 5  # Number of measurements to average at each point
# Seconds between measurements. Stability requires at least 0.2 sec or greater.
pauseMeasure = 0.5

"""---------------- USER NON-SERVICABLE PARTS ----------------"""

# Initialize the multimeter, clear and reset
rm = visa.ResourceManager('@py')
print(rm.list_resources())
keithley = rm.open_resource('USB0::1510::8448::8004460::0::INSTR')
keithley.write('*cls')
time.sleep(1)
keithley.write('*rst')
time.sleep(1)

""" Estimates the time measurements should take, and exits if the estimate
    is larger than the time between measurements (tCycles) """

estMeasTime = ((pauseMeasure+1.25)
               * nMeasureTypes * nMeas)+6  # Includes small fudge factor
# Calculate the minimum length between cycles
minTime = np.min(np.concatenate((initialTCycle, np.array([finalTCycle]))))
print("Data collection time estimate: {:0.2f} seconds,".format(estMeasTime),
      " minimum time between datapoints is {:0.2f} seconds".format(minTime))
if minTime >= estMeasTime:
    print("Data collection scheme ok, starting in 5 seconds")
    time.sleep(5)

else:
    print("not enough time to collect %d measurments",
          "between %d second intervals \n" % (nMeas, tCycles))
    print("increase seconds between measurements",
          " or lower number of replicates per point \n")
    print("closing in 5 seconds....")
    time.sleep(5)
    print("Exiting with error. goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()

if expTimeLength <= np.sum(initialTCycle):
    print("Warning: Total experiment length is less than total time",
          "of sample periods planned")

# Time points used for plotting. Note we use times in seconds.
timeNextPoint = time.time()
initialTime = time.time()
"""Data is stored as a dataframe, with a DateTime index corresponding
to exactly when the measurement was taken. Script tries to open previously
collected data first, or creates a new file."""
try:
    data = pd.read_csv('data.csv', index_col=0)
except FileNotFoundError:
    data = pd.DataFrame(columns=["Avg", "StdDev", "nMeas", "Type"])
time.sleep(2)
print("initial test measurement...")

# Attempt to read voltage to ensure multimeter is working.
voltage = keithley.query("measure:voltage:dc?")
if voltage == "":
    print("problem with Keithley. Stopping program in 5 seconds. ")
    print("power cycle Keithly and re-start program")
    time.sleep(5)
    print("Exiting with error. Goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()

print("Equipment OK, starting data collection\n")
time.sleep(2)
print("Starting initial measurement\n")
time.sleep(1)


measureNum = 0  # Marker for the measurement you're on

# Temporary values for plotting variables

scriptStartTime = time.asctime(time.localtime(time.time()))
timeVals = ([])
voltageVals = ([])
stdErrVals = ([])
xmin = ([])
ymin = ([])
ymax = ([])

plt.ion()  # Turns matplotlib interactive mode on.

while True:
    if time.time() >= timeNextPoint:
        # Variables for when measurements are taken
        try:
            # Use iterator to generate the next time point
            nextTCycle = next(tCycles)
        except StopIteration:
            # If you've reached the iterator end, use the final time
            nextTCycle = finalTCycle
        timeNextPoint = time.time()+nextTCycle
        measStartTime = time.time()
        if currentMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, nMeas,
                                          pauseMeasure, printVal=printVals,
                                          measType="current:dc")
            tempMeas.append("current:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas
            time.sleep(2)
        if resMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, nMeas,
                                          pauseMeasure, printVal=printVals,
                                          measType="resistance")
            tempMeas.append("resistance")
            data.loc[pd.to_datetime(t), :] = tempMeas
            time.sleep(2)
        if voltageMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, nMeas,
                                          pauseMeasure, printVal=printVals,
                                          measType="voltage:dc")
            tempMeas.append("voltage:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas
            time.sleep(2)
        measureNum += 1
        print("\nWriting data to file...")
        data.to_csv('data.csv')
        print("Complete!")
        actualMeasTime = ((time.time())-measStartTime)
        print("All measurements required a total of {:0.2f} seconds\n".format(
              actualMeasTime))
        timeToNextMeas = (timeNextPoint-(time.time()))
        print("{:0.2f} seconds until next round of measurements".format(
              timeToNextMeas))
        # Calculate time until next measurement for announcing purposes
        timeRemaining = timeToNextMeas-countdownTime

        # Plot voltage values live if possible.

        if plotVolt and voltageMeas:
            timeVals.append(pd.to_datetime(t))
            voltageVals.append(tempMeas[0])
            stdErrVals.append(tempMeas[1])
            [xmin, xmax] = [min(timeVals), max(timeVals)]
            # Set min and max y value by min/max value -/+ 2*max error
            [ymin, ymax] = [(min(voltageVals)-((max(stdErrVals))*2)),
                            (max(voltageVals)+((max(stdErrVals))*2))]
            ax1 = plt.gca()
            ax1.set_xlim([xmin, xmax])
            ax1.set_ylim([ymin, ymax])
            plt.errorbar(timeVals, voltageVals,
                         yerr=stdErrVals, fmt='o')
            plt.pause(0.05)
    # Stop execution if you reach the max time
    elif time.time() >= initialTime+expTimeLength:
        break
    # Play announcement if you've reached the appropriate time (timeRemaining)
    elif timeNextPoint-time.time() <= timeRemaining:
        endTime = (initialTime+expTimeLength)-(time.time())
        print("{:0.2f} seconds before next measurement,".format(timeRemaining),
              " and {:0.2f} seconds before end of experiment".format(endTime))
        timeRemaining -= countdownTime
# Close everything at end of execution.
print("Elapsed time: {:0.2f} seconds".format(timeNextPoint-initialTime))
print("Normal exit. Goodbye....")
keithley.write('system:local')
keithley.close()
