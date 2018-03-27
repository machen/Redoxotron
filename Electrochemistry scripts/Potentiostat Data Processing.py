import pandas as pd
import numpy as np
import re

dataPath = "R4_CurrentData.dat"

expParamRE = re.compile('(date,)(.)*')
expDataRE = re.compile('(Start run...)?(.)*')

isExpParam = False
isExpData = False
expNo = 0  # Index for the experiments

# Initialize data storage

expParamColumns = ['date', 'Exp name', 'Voltage (mV)', 'dac_gain value',
                   'actual dac gain', 'adc_gain', 'adc_gain_trim',
                   'ExpLength (s)', 'AveragingTime (s)', 'refersh_freq']
dataColumns = ['datetime', 'Current (A)', 'StdDev (A)', 'NPoints', 'expNo']

expParams = pd.DataFrame([], columns=expParamColumns)
expParams.index.name = 'Exp No'
expData = pd.DataFrame([], columns=dataColumns)

with open(dataPath, 'r') as file:
    for line in file:
        # Should parse if either experiment info or data
        if isExpParam:
            # Casts the various input strings as the correct types
            params = line.split(',')
            date = params[0]
            expName = params[1]
            voltage = float(params[2])
            dacGain = float(params[3])
            actualDacGain = float(params[4])
            adcGain = float(params[5])
            expLength = float(params[6])
            avgTime = float(params[7])
            refreshFreq = float(params[8])
            # Write exp params to data table
            expParams[expNo, :] = [date, expName, voltage, dacGain,
                                   actualDacGain, adcGain, expLength, avgTime,
                                   refreshFreq]
            expNo += 1
            isExpParam = False

        if expParamRE.match(line):
            isExpParam = True
            continue
        if expDataRE.match(line):
            isExpData = True
            continue
