import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import re
import seaborn as sns
sns.set_context('poster')

mpl.rcParams["lines.markersize"] = 3

workingDir = os.listdir()
filePat = re.compile('.*-current_voltage\.txt')
workingFiles = []
# Append possible working files
for item in workingDir:
    matches = re.match(filePat, item)
    if matches is not None:
        workingFiles.append(item)

if len(workingFiles) == 0:
    print("No files found. Aborting script.")
    quit()

f1 = plt.figure(1)
ax1 = f1.add_subplot(111)
f2 = plt.figure(2)
ax2 = f2.add_subplot(111)
peakData = pd.DataFrame([])
indexVal = 0
for fileName in workingFiles:
    data = pd.read_table(fileName, index_col=0, header=0)
    totSweep = np.max(data.loc[:, 'Scan'])
    for scanNum in range(1, totSweep+1):
        scanData = data.loc[data.loc[:, 'Scan'] == scanNum, :]
        # This line only for linear sweep data
        # scanData.sort_values(by='Voltage (mV)', ascending=True, inplace=True)
        volts = scanData.loc[:, 'Voltage (mV)']
        amps = scanData.loc[:, 'Current (A)']
        dAmps = np.diff(amps)/np.diff(volts)
        # if fileName.startswith('Oxic'):
        #     colorStr = 'b'
        # elif fileName.startswith('Anoxic'):
        #     colorStr = 'r'
        # else:
        #     colorStr = 'g'
        ax1.plot(volts, amps, label='Scan{} '.format(scanNum)+fileName,
                 marker='.', ls='none')  # , color=colorStr)
        # ax1.plot([100, 200], [0, 0], ls='-', color='k')
        ax2.plot(volts[:-1], dAmps,
                 label='Scan {} '.format(scanNum)+fileName,
                 marker='.', ls='none')  # , color=colorStr)
        # ax1.plot([0, 1], [0, 0], ls='-', color='k')
        """Section performs "peak finding," but is false if the data has skew
        (ie, as not been normalized to a background signal)."""
        peakData.loc[indexVal,
                     'File Name'] = fileName+' Scan {}'.format(scanNum)
        peakData.loc[indexVal,
                     'Anodic Peak (mV)'] = volts[np.argmax(amps)]
        peakData.loc[indexVal,
                     'Cathodic Peak (mV)'] = volts[np.argmin(amps)]
        peakData.loc[indexVal,
                     'Anodic Peak Current (A)'] = amps[np.argmax(amps)]
        peakData.loc[indexVal,
                     'Cathodic Peak Current (A)'] = amps[np.argmin(amps)]
        indexVal += 1

ax1.plot(peakData.loc[:, 'Anodic Peak (mV)'],
         peakData.loc[:, 'Anodic Peak Current (A)'], marker='o',
         color='k', ls='none', markersize=5)
ax1.plot(peakData.loc[:, 'Cathodic Peak (mV)'],
         peakData.loc[:, 'Cathodic Peak Current (A)'], marker='o',
         color='k', ls='none', markersize=5)
ax1.set_title('Individual Scans')
ax2.set_title('Individual Scans: Internal Resistance Corrected')
# ax1.set_xlim([160, 200])
# ax2.set_xlim([0.165, 0.185])
ax1.set_xlabel('Voltage (mV)')
ax1.set_ylabel('Current (A)')
ax2.set_xlabel('Voltage (mV)')
ax2.set_ylabel('Current entering the electrode (A)')
ax1.legend()
ax2.legend()
sns.despine()
plt.show()
