import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt

"""CHANGE THIS TO WRITE DATETIMES TOO FOR WHEN THE SAMPLE WAS MEASURED???"""


workingDir = 'Redoxotron 7\\Electrical Data'
finalPrefix = 'Redoxotron 7'
finalName = finalPrefix+' All.csv'
fullData = pd.DataFrame(columns=['Elapsed Time (s)', 'Voltage (mV)', 'Current (A)'])
averageData = True
avgWindow = 100
avgName = finalPrefix+'_{} Window.csv'.format(avgWindow)
initialTime = '6/15/2018 15:27'


# Get list of data files

files = os.listdir(workingDir)
fileList = []
for name in files:
    if name == finalName:
        continue
    elif name.endswith('.csv'):
        fileList.append(name)
    else:
        continue

initialTime = pd.to_datetime(initialTime)

# Diagnostic figure to ensure times/currents do not overlap

f1 = plt.figure(2)
ax1 = f1.add_subplot(111)

# Iterate over available .csv files and load their data into the main output file

for dataFile in fileList:
    fileLoc = workingDir+'\\'+dataFile
    with open(fileLoc, 'r') as info:
        for line in info:
            # If time, strip out time
            if line.startswith("Experimental start"):
                expStart = line.replace("Experimental start: ", "")
                expOffset = pd.to_datetime(expStart)-initialTime
                expOffset = expOffset.total_seconds()
            # If gain, strip out gain
            if line.startswith("Gain value: "):
                gain = float(line.replace("Gain value: ", ""))
            # If voltage, strip out voltage
            if line.startswith("Experimental voltage: "):
                voltage = line.replace("Experimental voltage: ", "")
                voltage = float(voltage.replace(" mV", ""))
            # If Elapsed time, exit
            if line.startswith("Elapsed Time"):
                break
    data = pd.read_csv(fileLoc, header=3, dtype={'Elapsed Time (s)':
                       np.float64, 'Current (A)': np.float64})
    # Fix entries that had multiple steps
    data.loc[:, 'NewStep'] = data.loc[:, 'Elapsed Time (s)'].lt(data.loc[:, "Elapsed Time (s)"].shift())
    shiftedMarker = data.index[data.loc[:, 'NewStep']]
    offSet = 65534
    for pos in shiftedMarker:
        data.loc[pos:, "Elapsed Time (s)"] += offSet

    data.loc[:, 'Elapsed Time (s)'] = expOffset + data.loc[:, 'Elapsed Time (s)']
    timeDeltas = pd.to_timedelta(data.loc[:, "Elapsed Time (s)"], unit="s")
    data.loc[:, 'Sample time'] = initialTime+timeDeltas
    data.loc[:, 'Voltage (mV)'] = voltage
    ax1.plot(data.loc[:, 'Elapsed Time (s)']/60.0/60.0,
             data.loc[:, 'Current (A)'], label=dataFile, ls=None)
    plt.ion()
    plt.show()
    fullData = fullData.append(data, ignore_index=True)

fullData.to_csv(workingDir+'\\'+finalName)
print('Data Written, moving to average')
if averageData:
    avgRes = pd.DataFrame(columns=['Elapsed Time (s)', 'Current (A)', 'stdCurrent (A)'])
    firstIndex = 0
    ptNum = 0
    while firstIndex+avgWindow < max(fullData.index):
        print(firstIndex)
        lastIndex = firstIndex+avgWindow-1
        subData = fullData.loc[firstIndex:lastIndex, :]
        avgRes.loc[ptNum, 'Elapsed Time (s)'] = np.mean(subData.loc[:,
                                                        'Elapsed Time (s)'])
        avgRes.loc[ptNum, 'Current (A)'] = np.mean(subData.loc[:,
                                                               'Current (A)'])
        avgRes.loc[ptNum, 'stdCurrent (A)'] = np.std(subData.loc[:,
                                                                 'Current (A)'])
        avgRes.loc[ptNum, 'Voltage (mV)'] = np.mean(subData.loc[:,
                                                                'Voltage (mV)'])
        ptNum += 1
        firstIndex += avgWindow
    avgRes.to_csv(workingDir+'\\'+avgName)
