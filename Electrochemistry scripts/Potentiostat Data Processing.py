import pandas as pd
import datetime as dt
import re

dataPath = "R4_CurrentData.dat"

expParamRE = re.compile('(date,)(.)*')
expDataRE = re.compile('(Start run...){1}(.)*')

isExpParam = False
isExpData = False
expNo = 0  # Index for the experiments
dataIndex = 0
timeFmt = '%Y-%m-%d %H:%M:%S'

# Initialize data storage

expParamColumns = ['date', 'Exp name', 'Voltage (mV)', 'dac_gain value',
                   'actual dac gain', 'adc_gain', 'adc_gain_trim',
                   'ExpLength (s)', 'AveragingTime (s)', 'refersh_freq']
dataColumns = ['Time from start (s)', 'Current (A)', 'StdDev (A)', 'NPoints',
               'expNo']

expParams = pd.DataFrame([], columns=expParamColumns)
expParams.index.name = 'Exp No'

expData = pd.DataFrame([], columns=dataColumns)
expData.index.name = 'Measurement No'

with open(dataPath, 'r') as file:
    for line in file:
        # Should parse if either experiment info or data
        if isExpParam:
            # Casts the various input strings as the correct types
            params = line.split(',')
            try:
                # Need to convert Unix dates to regular dates
                params[0] = dt.datetime.fromtimestamp(float(params[0]))\
                                          .strftime(timeFmt)
            except ValueError:
                pass
            date = params[0]
            expName = params[1]
            voltage = float(params[2])
            dacGain = float(params[3])
            actualDacGain = float(params[4])
            adcGain = float(params[5])
            adcTrim = float(params[6])
            expLength = float(params[7])
            avgTime = float(params[8])
            refreshFreq = float(params[9])
            # Write exp params to data table
            expParams.loc[expNo, :] = [date, expName, voltage, dacGain,
                                       actualDacGain, adcGain, adcTrim,
                                       expLength, avgTime, refreshFreq]
            expNo += 1
            isExpParam = False
        if isExpData:
            if line in ['\n', '\r\n']:
                isExpData = False
                continue
            else:
                data = line.strip('[]\n')
                data = data.split(',')
                pos = 0
                for item in data:
                    # Need to convert elapsed times to dates, and unix time stamps
                    if pos == 0:
                        item = float(item)
                        if item > 1E8:
                            item = dt.datetime.strftime(timeFmt)
                        else:
                            item = dt.timedelta(seconds=item)
                            item = dt.datetime.strptime(date, timeFmt)+item
                    posLabel = dataColumns[pos]
                    expData.loc[dataIndex, posLabel] = item
                    pos += 1
                expData.loc[dataIndex, 'expNo'] = expNo
                dataIndex += 1
        if expParamRE.match(line):
            isExpParam = True
            continue
        if expDataRE.match(line):
            isExpData = True
            continue
expData.to_csv('Experimental Data.csv')
expParams.to_csv('Experiment Parameters.csv')
