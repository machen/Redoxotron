# import numpy as np
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
for fileName in workingFiles:
    data = pd.read_table(fileName, index_col=0, header=0)
    data.sort_values(by='Voltage (mV)', ascending=True, inplace=True)
    volts = data.loc[:, 'Voltage (mV)']
    amps = data.loc[:, 'Current (A)']
    ax1.plot(amps, volts, label=fileName, marker='.', ls=None)
    ax1.set_title('Individual Scans')
    ax1.plot([0, 0], [100, 200], ls='-', color='k')
ax1.set_ylim([160, 200])
plt.legend()
sns.despine()
plt.show()
