import os
import re
import pandas as pd
import matplotlib.pyplot as plt
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
plt.ion()
for fileName in workingFiles:
    data = pd.read_csv(fileName, index_col=None)
    data.loc[:, 'Date'] = pd.to_datetime(data.loc[:, 'Date'])
    # Calculate the elapsed seconds to plot rather than using dates
    initialTime = data.loc[0, 'Date']
    elapsedTime = data.loc[:, 'Date'] - initialTime
    data.loc[:, 'ElapsedTime(s)'] = elapsedTime.dt.total_seconds()
    markers = iT.cycle(['.', 'o', 's', '^'])  # Markers for diff. data types
    for dataType in data.loc[:, 'Type'].unique():
        typeMark = next(markers)
        subData = data.loc[data.loc[:, 'Type'] == dataType, :]
        ax1.errorbar(data.loc[:, 'ElapsedTime(s)']/60.0/60.0,
                     data.loc[:, 'Avg'], yerr=data.loc[:, 'StdDev'], ls='none',
                     marker=typeMark, label=dataType)
        ax1.set_xlabel("Time Elapsed (hrs)")
        ax1.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
        ax2.errorbar(data.loc[:, 'ElapsedTime(s)'],
                     data.loc[:, 'Avg'], yerr=data.loc[:, 'StdDev'], ls='none',
                     marker=typeMark, label=dataType)
        ax2.set_xlim([-100, 1.5*60*60.0])
        ax2.set_ylim([3.0E-3, 6.1E-3])
        ax2.set_xlabel("Time elapsed (s)")
        ax2.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
    ax1.legend()
    ax2.legend()
    data.to_csv(fileName[:-4]+" Result.csv", index_label="Date/Time")
sns.despine(fig=f1)
sns.despine(fig=f2)
f1.savefig('WholeTime.svg', fmt='svg', dpi=1000)
f2.savefig('90min.svg', fmt='svg', dpi=1000)
plt.show()
