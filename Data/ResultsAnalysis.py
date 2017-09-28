import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
    exit()

# Initialize figures
f1 = plt.figure(1)
ax1 = f1.add_subplot(111)
plt.ion()

for fileName in workingFiles:
    data = pd.read_csv(fileName, index_col=None)
    data.loc[:, 'Date'] = pd.to_datetime(data.loc[:, 'Date'])
    # Calculate the elapsed seconds to plot rather than using dates
    initialTime = data.loc[0, 'Date']
    elapsedTime = data.loc[:, 'Date'] - initialTime
    data.loc[:, 'ElapsedTime(s)'] = elapsedTime.dt.total_seconds()/60.0/60.0
    for dataType in data.loc[:, 'Type'].unique():
        subData = data.loc[data.loc[:, 'Type'] == dataType, :]
        ax1.errorbar(data.loc[:, 'ElapsedTime(s)'], data.loc[:, 'Avg'],
                     yerr=data.loc[:, 'StdDev'], ls='none', marker='.',
                     label=dataType)
    plt.legend()

sns.despine()
plt.show()
