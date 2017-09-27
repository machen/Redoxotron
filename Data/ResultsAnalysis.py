import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

""" Script is designed to be run on the single csv here
user should move files out"""
workingDir = os.listdir()
filePat = re.compile('.*Data\.csv')
workingFiles = []
# Append possible working files
for item in workingDir:
    matches = re.match(filePat, item)
    if matches is not None:
        workingFiles.append(item)

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
    # Should make this smarter if there multiple types
    for dataType in data.loc[:, 'Type'].unique():
        subData = data.loc[data.loc[:, 'Type'] == dataType, :]
        ax1.errorbar(data.loc[:, 'ElapsedTime(s)'], data.loc[:, 'Avg'],
                     yerr=data.loc[:, 'StdDev'], ls='none', marker='.',
                     label=dataType)
        plt.legend()

sns.despine()
plt.show()
