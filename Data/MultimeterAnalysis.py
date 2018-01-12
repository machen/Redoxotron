import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import itertools as iT

""" Script is designed to be run on the csvs here
user should move files out
TO DO:
1) Plot figures separately for each file
2) Find a way to calculate the current flow using the inputs
3) Write data to file
4) Incorporate chemical measurements
"""

mpl.rcParams["lines.markersize"] = 4

workingDir = os.listdir()
filePat = re.compile('.*Data\.csv')
workingFiles = []
# Append possible working files
for item in workingDir:
    matches = re.match(filePat, item)
    if matches is not None:
        workingFiles.append(item)

if len(workingFiles) == 0:
    print("No files found. Aborting script.")
    quit()

# Initialize figures
f1 = plt.figure(1)
ax1 = f1.add_subplot(111)
f2 = plt.figure(2)
ax2 = f2.add_subplot(111)
f3 = plt.figure(3)
ax3 = f3.add_subplot(111)
plt.ion()
for fileName in workingFiles:
    data = pd.read_csv(fileName, index_col=None)
    data.loc[:, 'Date'] = pd.to_datetime(data.loc[:, 'Date'])
    # Calculate the elapsed seconds to plot rather than using dates
    initialTime = data.loc[142, 'Date']
    elapsedTime = data.loc[:, 'Date'] - initialTime
    data.loc[:, 'ElapsedTime(s)'] = elapsedTime.dt.total_seconds()
    markers = iT.cycle(['o', 's', '^', 'x'])  # Markers for diff. data types
    for dataType in data.loc[:, 'Type'].unique():
        typeMark = next(markers)
        subData = data.loc[data.loc[:, 'Type'] == dataType, :]
        ax1.errorbar(subData.loc[:, 'ElapsedTime(s)']/60.0/60.0,
                     subData.loc[:, 'Avg']*1000, yerr=subData.loc[:, 'StdDev']*1000, ls='none',
                     marker=typeMark, label=dataType)
        ax1.set_xlabel("Time Elapsed (hrs)")
        ax1.set_ylabel("Voltage (mV)")
        ax1.ticklabel_format(style='sci', axis='y', scilimits=(-3, 3))
        ax2.errorbar(subData.loc[:, 'ElapsedTime(s)']/60.0/60.0,
                     subData.loc[:, 'Avg']*1000, yerr=subData.loc[:, 'StdDev']*1000, ls='none',
                     marker=typeMark, label=dataType)
        ax2.plot([-10, 600], [0.0, 0.0], 'k')
        ax2.set_ylim([-6, 1])
        ax2.set_xlim([-0.1, 20])
        ax2.set_xlabel("Time elapsed (hrs)")
        ax2.set_ylabel("Voltage (mV)")
        ax2.ticklabel_format(style='sci', axis='y', scilimits=(-3, 3))
        ax3.errorbar(subData.loc[:, 'ElapsedTime(s)']/60.0/60.0,
                     subData.loc[:, 'Avg']*1000, yerr=subData.loc[:, 'StdDev']*1000, ls='none',
                     marker=typeMark, label=dataType)
        ax3.plot([-1, 30*24], [0.0, 0.0], 'k')
        ax3.set_xlabel("Time elapsed (hrs)")
        ax3.set_ylabel("Voltage (mV)")
        ax3.set_ylim([-1, 0.3])
    ax1.legend()
    ax2.legend()
    ax3.legend()
    data.to_csv(fileName[:-4]+" Result.csv", index_label="Date/Time")
sns.despine(fig=f1)
sns.despine(fig=f2)
# f1.savefig('WholeTime.svg', fmt='svg', dpi=1000)
# f2.savefig('LowVoltage.svg', fmt='svg', dpi=1000)
plt.show()
