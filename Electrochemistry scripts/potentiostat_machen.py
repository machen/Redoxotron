"""
TO DO LIST:
1) Rewrite major functionality

    b) Start experiment
        Need to be checked
    c) Read in data
        Needs to be checked
    d) Output data to some type of file
        Needs to be implemented
2) Handling for non-data lines (based on ben's code, known to happen)
    Could catch errors and output problematic line to log
    Should catch serial errors and exit
"""

import serial
import time
import numpy as np
import datetime as dt
import struct
import csv
import os.path

logFile = 'CommandLog.log'  # USER EDITED, path for output log
serialPort = '/dev/ttyACM0'  # USER EDITED, path to serial port
gain = 2  # USER EDITED, transducer gain, see DStat documentation
dataFile = 'Test'  # USER EDITED, path for dataFile
expLength = 600  # USER EDITED, Seconds, length of experiment
expVolt = 100  # USER EDITED, mV, target voltage
reportTime = 30  # USER EDITED, Seconds, time for reporting averages


class Error(Exception):
    """ Base class for exceptions. """
    pass


class CommunicationsError(Error):
    """Error class for failed communications to dstat"""
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class ParameterUploadError(Error):
    """Error class for failed parameter upload"""
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def writeCmdLog(logFile, type, cmd, timeFmt='%m/%d/%Y %H:%M:%S.%f',
                time=dt.datetime.today()):
    if not logFile:
        return
    with open(logFile, 'a') as log:
        if type is 'User':
            log.write(' Time: '+time.strftime(timeFmt)+', U: '+cmd.rstrip()+'\n')
        elif type is 'DStat':
            log.write(' Time: '+time.strftime(timeFmt)+', D: '+cmd.rstrip()+'\n')
        else:
            log.write(' Time: '+time.strftime(timeFmt)+', ?: '+cmd.rstrip()+'\n')
        return


def sendCommand(ser, cmd, tries=10, logFile=None):
    # sendCommand only sends the command and checks that it's been received properly
    # Checking of the responses (ie for issues with parameters) need to be handled outside of the function
    cmd = cmd.rstrip()
    ser.reset_input_buffer()
    cmdInitStr = b'!'+str(len(cmd)).encode("UTF-8")+b'\n'
    ser.write(cmdInitStr)  # Write initiator command
    writeCmdLog(logFile, 'User', cmdInitStr.decode())
    if len(cmd) == 0:  # 0 len cmd gives only a test. This tests for response
        for i in range(tries):
            reply = ser.readline()
            writeCmdLog(logFile, 'DStat', reply.decode())
            if reply.rstrip() == b"@ACK 0":
                reply = ser.readline()
                writeCmdLog(logFile, 'DStat', reply.decode())
                if reply.rstrip() == b"@RCV 0":
                    return True
            else:
                time.sleep(0.5)
                ser.reset_input_buffer()
                ser.write(cmdInitStr)
                writeCmdLog(logFile, 'User', cmdInitStr.decode())
                time.sleep(0.1)
        return False
    elif cmd is 'R':
        # A successful reset command will disconnect the USB, so we need to skip the checks
        for i in range(tries):
            ackRpl = b'@ACK '+str(len(cmd)).encode("UTF-8")
            reply = ser.readline()
            writeCmdLog(logFile, 'DStat', reply.decode())
            if reply.rstrip() == ackRpl:
                cmdStr = cmd+'\n'
                ser.write(cmdStr.encode('UTF-8'))  # Write command with ack msg if we get it
                writeCmdLog(logFile, 'User', cmdStr)
                return True
            else:
                time.sleep(0.5)
                ser.reset_input_buffer()
                ser.write(cmdInitStr)
                writeCmdLog(logFile, 'User', cmdInitStr)
                time.sleep(0.1)
    else:
        for i in range(tries):
            ackRpl = b'@ACK '+str(len(cmd)).encode("UTF-8")
            reply = ser.readline()
            writeCmdLog(logFile, 'DStat', reply.decode())
            if reply.rstrip() == ackRpl:
                cmdStr = cmd+'\n'
                ser.write(cmdStr.encode('UTF-8'))  # Write command with ack msg if we get it
                writeCmdLog(logFile, 'User', cmdStr)
                for j in range(tries):
                    rplRpl = b'@RCV '+str(len(cmd)).encode("UTF-8")
                    reply = ser.readline()
                    writeCmdLog(logFile, 'DStat', reply.decode())
                    if reply.rstrip() == rplRpl:
                        return True
                    else:
                        time.sleep(0.5)
                        ser.reset_input_buffer()
                        ser.write(cmdStr.encode('UTF-8'))
                        writeCmdLog(logFile, 'User', cmdStr)
                        time.sleep(0.1)
                print('Failed to send and receive command: '+cmd)
                return False
            else:
                time.sleep(0.5)
                ser.reset_input_buffer()
                ser.write(cmdInitStr)
                writeCmdLog(logFile, 'User', cmdInitStr)
                time.sleep(0.1)
        print('Failed to send and recieve acknowledgement')
        return False


def initializeDStat(path, timeout=3, logFile=None):
    try:
        for i in range(0, 10):
            ser = serial.Serial(path, rtscts=True, timeout=timeout,
                                write_timeout=timeout)
    except serial.SerialException:
        ser = None
        pass
        # basePortNum = path[-1]
        # basePath = path[:-1]  # Naively tries to iterate through numbered ports
        # for portNum in range(0, 9):
        #     if portNum == int(basePortNum):
        #         continue
        #     newPath = basePath+str(portNum)
        #     try:
        #         ser = serial.Serial(newPath, rtscts=True, timeout=timeout,
        #                             write_timeout=timeout)
        #     except serial.SerialException:
        #         ser = None
        #         continue
        # if not ser:
        #     raise serial.SerialException('Could not find correct serial port')
        # path = newPath
    if not ser:
        raise serial.SerialException('Could not connect to serial port')
    if sendCommand(ser, '', logFile=logFile):  # test empty command
        return ser
    else:
        raise CommunicationsError(ser.name, "DStat read/write test failed.")


def readParamResponse(ser, logFile=None, time=dt.datetime.today()):
    reply = ser.readlines()
    for line in reply:
        if line.startswith(b'#'):
            writeCmdLog(logFile, 'DStat', line.decode(), time=time)
        elif line.rstrip() == b'@DONE':
            writeCmdLog(logFile, 'DStat', line.decode(), time=time)
            return True  # If command completes, returns True
        else:
            print('Unexpected Response from DStat, Check Log')
            writeCmdLog(logFile, 'DStat', line.decode(), time=time)
    return False  # Should give a "fail" state if the @DONE reply is not recieved


def setDStatParams(ser, gain=2, logFile=None):
    try:
        # Try set adc
        adcSet = sendCommand(ser, 'EA2 03 1')  # No need to change ADC settings
        adcTime = dt.datetime.today()
        if adcSet:
            adcResp = readParamResponse(ser, logFile=logFile, time=adcTime)
        else:
            print("Writing ADC Params Failed")
        gainSet = sendCommand(ser, 'EG'+str(gain))
        gainTime = dt.datetime.today()
        if gainSet:
            gainResp = readParamResponse(ser, logFile=logFile, time=gainTime)
        else:
            print("Writing Gain Params Failed")
        return adcResp, gainResp
    except serial.SerialException:
        print("Problems with Serial Port, Parameters are not uploaded")
        return False, False


def resetDStat(ser):
    print('WARNING: FUNCTION WILL LIKELY FAIL')
    path = ser.name
    attempt = sendCommand(ser, 'R')
    ser.close()
    if attempt:
        ser = initializeDStat(path)
        return ser
    else:
        raise CommunicationsError(path, 'Reset has failed.')


def convertCurrent(adcCode, gain, pgaGain=2):
    # Assumes that PGA value is 2. Will need to edit otherwise.
    gainValues = {0: 1, 1: 100, 2: 3000, 3: 3E4, 4: 3E5, 5: 3E6, 6: 3E7,
                  7: 1E8}
    current = (float(adcCode)/(pgaGain/2))*(1.5*gainValues[gain]/8388607)
    return current


def runExperiment(ser, expLength, gain, expVolt, logFile=None,
                  dataFile='Test', rptTime=300,
                  timeFmtStr='%m/%d/%Y %H:%M:%S.%f'):
    expInit = sendCommand(ser, 'ER1 0')
    if expInit:
        reply = ser.readlines()
        for line in reply:
            if line.startswith(b'#'):
                writeCmdLog(logFile, 'DStat', line.decode())
            elif line.startswith(b'@RQP'):
                writeCmdLog(logFile, 'DStat', line.decode())
                break
            else:
                print('Unexpected response from DStat logged. Continuing.')
                writeCmdLog(logFile, 'DStat', line.decode(), timeFmt=timeFmtStr)
        try:
            dacVolt = int(65536.0/3000*expVolt+32768)  # Experimental voltage should be reported in millivolts
            expStr = str(dacVolt)+'\n'
            ser.write(expStr.encode("UTF-8"))
            expStr = str(expLength)+'\n'
            ser.write(expStr.encode("UTF-8"))
        except serial.SerialException:
            print('Error Writing Voltage/Time to serial port')
            return False
        print('Experimental parameters uploaded')
        startTime = dt.datetime.today()
        writeCmdLog(logFile, 'User', expStr, timeFmt=timeFmtStr,
                    time=startTime)
        # Create dataFile
        if os.path.isfile(dataFile+'.csv'):
            # Make a new file if the data file already exists
            dataFile = dataFile+'new.csv'
        else:
            dataFile = dataFile+'.csv'
        with open(dataFile, 'a') as outFile:
            dataWriter = csv.writer(outFile, dialect='excel')
            dataWriter.writerow(['Experimental start: ' +
                                startTime.strftime(timeFmtStr)])
            dataWriter.writerow(['Gain value: '+str(gainValues[gain])])
            dataWriter.writerow(['Elapsed Time (s)', 'Current (A)'])
        # Initialize averaging arrays
        currentVals = []
        timeVals = []
        rptTime = dt.timedelta(seconds=rptTime)
        checkTime = dt.datetime.today()
        interval = checkTime-startTime
        reply = ser.readline()
        while reply.rstrip() != b'@DONE':
            if ser.in_waiting == 0:
                time.sleep(0.1)
                # Don't want to try to readlines on empty serial port
                continue
            reply = ser.readline()
            if reply.startswith(b'#') or reply.startswith(b'@'):
                # Log informational messages and reports from DStat
                writeCmdLog(logFile, 'DStat', reply.decode())
                continue
            elif reply == b'B\n':
                # Catch data line
                try:
                    reply = ser.readline()
                except serial.SerialException:
                    print('Serial problems, aborting experiment')
                    return False
                data = reply.rstrip()  # Remove newline
                try:
                    sec, millisec, curr = struct.unpack('<HHl', data)
                    newTimeVal = float(sec)+float(millisec/1000.0)
                    newCurrVal = convertCurrent(curr, gain)
                    timeVals.append(newTimeVal)
                    currentVals.append(newCurrVal)
                    with open(dataFile, 'a') as outFile:
                        dataWriter = csv.writer(outFile, dialect='excel')
                        dataWriter.writerow([newTimeVal, newCurrVal])
                except struct.error:
                    print("Formatting problem, line written to log, continuing")
                    try:
                        writeCmdLog(logFile, 'DStat', reply.decode(),
                                    time=dt.datetime.today())
                    except UnicodeDecodeError as e:  # NEed to catch the correct exception
                        print(e)
                        print('Problematic command not logged')
                        pass
                    pass
                interval = dt.datetime.today()-checkTime
                if interval >= rptTime:
                    print('Time: '+dt.datetime.today().strftime(timeFmtStr)
                          + ', Average Current: '+str(np.mean(currentVals)))
                    checkTime = dt.datetime.today()
                continue
        print('Experiment Completed')
        return True

    else:
        print('Failed to initialize experiment')
        return False


timeFmtStr = '%m/%d/%Y %H:%M:%S.%f'
gainValues = {0: 1, 1: 100, 2: 3000, 3: 3E4, 4: 3E5, 5: 3E6, 6: 3E7,
              7: 1E8}
with initializeDStat(serialPort, logFile=logFile) as ser:  # Ensures closure of port on failure
    print('DStat Initialized')
    sendCommand(ser, 'V')
    print(ser.readlines())
    adcSet, gainSet = setDStatParams(ser, gain=gain, logFile=logFile)
    if not adcSet:
        raise ParameterUploadError('ADC', 'Check comms with DStat')
    if not gainSet:
        raise ParameterUploadError(gain, 'Check for correct gain')
    print('Parameters uploaded')
    exp = runExperiment(ser, expLength, gain, expVolt,
                        logFile=logFile, dataFile=dataFile,
                        rptTime=reportTime)
