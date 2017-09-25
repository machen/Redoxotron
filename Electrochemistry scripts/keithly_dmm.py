import visa
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""TO DO LIST:
2) Enable variable timing
3) Prevent and log errors encountered by multimeter during run
4) Catch KeyboardInterrupt in main loop and close resource on interrupt
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
plotVolt = True  # Plot voltage data in real-time?
printVals = True  # print measurements in loop

""" Choose measurements (set to True to enable measurement).
    Note that the multimeter must be set up to take said measurements!"""

nMeasureTypes = 1
resMeas = False
currentMeas = False
voltageMeas = True

countdownTime = 5  # Sets interval for announcing next measurement

expTimeLength = 3600  # Script run time in seconds
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

timeNextPoint = time.time()
initialTime = time.time()
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
        timeNextPoint = time.time()+tCycles
        measStartTime = time.time()
        if currentMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=printVals,
                                          measType="current:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("current:dc")
            time.sleep(2)
        if resMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=printVals,
                                          measType="resistance")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("resistance")
            time.sleep(2)
        if voltageMeas:
            t, tempMeas = takeMeasurement(keithley, measureNum, numpoints,
                                          pauseMeasure, printVal=printVals,
                                          measType="voltage:dc")
            data.loc[pd.to_datetime(t), :] = tempMeas.append("voltage:dc")
            time.sleep(2)
        measureNum += 1
        print("\nWriting data to file...")
        data.to_csv('data.csv')
        print("Complete!")
        actualMeasTime = ((time.time())-measStartTime)
        print("All measurements required a total of {:f} seconds\n".format(
              actualMeasTime))
        timeToNextMeas = (timeNextPoint-(time.time()))
        print("{:d} seconds until next round of measurements".format(
              timeToNextMeas))
        timeRemaining = timeToNextMeas-countdownTime

        # Plot voltage values live. Requires voltageMeas to be true!

        if plotVolt:
            timeVals.append(t)
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

    elif time.time() >= initialTime+expTimeLength:
        break

    elif timeNextPoint-time.time() <= timeRemaining:
        endtime = (initialTime+expTimeLength)-(time.time())
        print("{:d} seconds before next measurement,".format(timeRemaining),
              " and {:d} seconds before end of experiment".format(endtime))
        timeRemaining -= countdownTime

print("Elapsed time: {:f} seconds".format(timeNextPoint-initialTime))
print("Normal exit. Goodbye....")
keithley.write('system:local')
keithley.close()
