"""
TO DO LIST:
1) Add option to average data over time
2) Fix output of times for multistage experiment (currently, times reset after max)
3) Check logging (ultimately the problematic lines are... junk)
3) Work on getting a restart to work
"""
import serial
import time
import numpy as np
import datetime as dt
import struct
import csv
import os.path

"""Script will end on its own, however, if it needs to terminated prematurely,
ctrl+C will cleanly close the serial port."""

"""SCRIPT PARAMETERS HERE"""

logFile = 'Redoxotron4_Test2_CmdLog.log'  # USER EDITED, Defined path for log of commands between DStat and Script
serialPort = '/dev/ttyACM0'  # USER EDITED, Path to serial port. To check if it's there, run in a terminal: "python -m serial.tools.list_ports"
gain = 1  # USER EDITED, transducer gain, see DStat documentation.
# Gains allowed by dstat. use lowest value to detect targeted current diffs
# define POT_GAIN_0 0
# define POT_GAIN_100 1
# define POT_GAIN_3k 2
# define POT_GAIN_30k 3
# define POT_GAIN_300k 4
# define POT_GAIN_3M 5
# define POT_GAIN_30M 6
# define POT_GAIN_100M 7
dataFile = 'Redoxotron4_Test2'  # USER EDITED, path for dataFile
expLength = 72*60*60  # USER EDITED, Seconds, length of experiment. INTEGER ONLY.
"""Note that experimental times greater than ~65000 seconds will be broken into multiple experiments,
which will have to be adjusted during data handling. An example will be given.
"""
expVolt = 1000  # USER EDITED, mV, target voltage. Positive voltages are oxidizing, negative voltages are reducing
reportTime = 300  # USER EDITED, Seconds, time for reporting averages

"""MAIN SCRIPT HERE, ALTER AT YOUR OWN RISK"""

"""ERROR CLASS DEFINITIONS. USED FOR ERROR HANDLING"""

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

class ExperimentalError(Error):
    """Error class for failed experiment"""
    def __init__(self, message):
        self.message = message


def fileNameCheck(filePath, num=0, ext=".csv"):
    """Recursive function checks to see if a file exists by filePath+ext,
    and if it does, returns a path with a number added, which is automatically
    incremented. For example: If "test.csv" exists, then the returned path
    will be "text_1.csv"

    VARIABLES:

    filePath: String defining the path to the log file, without the extension
    num: Int. Iteration number. Should not need to be specified when calling the function.
    ext: String. The defined file path extension.

    RETURNS: A string, containing a complete, non-redundant file path
    """
    if num == 0:
        path = filePath
    elif num == 1:
        path = filePath+"_{}".format(num)
    elif num > 1:
        path = filePath.replace("_{}".format(num-1), "_{}".format(num))
    if os.path.isfile(path+ext):
        path = fileNameCheck(path, num+1)
        return path
    else:
        return path+ext


def writeCmdLog(logFile, type, cmd, timeFmt='%m/%d/%Y %H:%M:%S.%f',
                time=dt.datetime.today()):
    """Function writes the given command to the command log using a time stamp
    and indicating who sent the command (user to Dstat vs Dstat to user)

    VARIABLES:
    logFile: String. File path for the command log. Include the extension!
    Type: Either "User" or "DStat". Other commands will be logged, but without
    indication of who wrote the command.the
    cmd: String. Command to be written. Generally, this should be string converted output
    directly from the dstat, or strings written to the dstat (not raw).
    timeFmt: String for formatting the times. Default is "m/d/y H:M:S.s"
    time: DateTime. Time command was logged. Defaults to time the command is called.

    RETURNS: Nothing.

    """
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
    """# sendCommand only sends the command and checks that it's been received properly.
    Checking of the responses (ie for issues with parameters)
    need to be handled outside of the function.
    Notably this handles the transmission protocol for the dstat, which requires
    writing "!n\n" where n is the number of characters you want to send

    VARIABLES:
    ser: Serial object. Serial port object for the DStat.
    cmd: String. Command to send. Include only the letters (ie. EA or R).
    tries: Int. Number of attempts to send the command
    logFile: String. Path to command log

    RETURN: True for successful command write and receive, False for failure.
    Note success requires a) writing the command, and b) receiving the correct replies.
    """
    cmd = cmd.rstrip()
    ser.reset_input_buffer()
    cmdInitStr = b'!'+str(len(cmd)).encode("UTF-8")+b'\n'
    ser.write(cmdInitStr)  # Write initiator command
    writeCmdLog(logFile, 'User', cmdInitStr.decode())
    if len(cmd) == 0:  # 0 len cmd gives only a test. This tests for response only.
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
    else: # Handles all other commands.
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
    """Initializes the DStat, and runs a blank command test to make
    sure the DStat is ready for read/write

    VARIABLES:

    Path: String defining the serial port path.
    timeout: Int or float defining timeout for serial port
    LogFile: String for the command log.

    RETURNS: Serial object for DStat. If it fails, a serial exception is raised."""

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
    """Reads the parameter responses from the DStat. Correctly upload parameters
    should recieve a specific reply ultimately. If not recieved, then parameter upload has failed.

    VARIABLES:

    Ser: Serial port object for the DStat. Should already be open.be
    logFile: String. Path to the command log.
    Time: Datetime. Defaults to time of function call.

    RETURNS: True for successful parameter reply sequence. False for failed.
    """
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
    """Sets the gain and ADC settings as specified in the user parameter section.

    VARIABLES:

    ser: Serial object for DStat
    Gain: DStat gain value (see table in user edited section). Default is 2.
    logFile: String to command log.

    RETURNS: adcResp, gainResp, booleans corresponding to the succcess of
    setting the parameters.

    """

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


def initializeExperiment(ser, expLength, expVolt, logFile=None,
                         timeFmtStr='%m/%d/%Y %H:%M:%S.%f'):
    """Initializes the experiment on the DStat.
    Correctly handles experimental times that are too long for DStat.for

    VARIABLES:

    ser: Serial port object for the DStat
    expLength: Int. Number of seconds to run the experiment.the
    expVolt: Experimental voltage setpoint in millivolts. Negative is reducing, positive is oxidizing.
    logFile: String to path for the command log.
    timeFmtStr: Format for writing time formats.

    RETURNS: True for successful experimental initialization, False otherwise.
    """

    maxLength = 65534
    if expLength > maxLength:
        print('Experiment length is too long for single step, will be run in multiple steps')
        nSteps = int(expLength/maxLength)
        timeArray = [65534]*nSteps  # Initialize array of time steps
        if expLength % maxLength > 0:
            nSteps += 1
            timeArray.append(expLength % maxLength)
    else:
        nSteps = 1
        timeArray = [expLength]
    try:
        expInitCmd = 'ER{} 0\n'.format(nSteps)
        expInit = sendCommand(ser, expInitCmd)
        if expInit:
            time.sleep(1)  # Give the dstat a chance to process
            reply = ser.readlines()
            # Check for correct replies
            for line in reply:
                if line.startswith(b'#'):
                    writeCmdLog(logFile, 'DStat', line.decode())
                elif line.startswith(b'@RQP'):
                    writeCmdLog(logFile, 'DStat', line.decode())
                    break  # Continue as dstat is now asking for the parameters
                else:
                    print('Unexpected response from DStat logged. Continuing.')
                    writeCmdLog(logFile, 'DStat', line.decode(), timeFmt=timeFmtStr)
            # Write the parameters: first the voltage steps, then the time steps
            dacVolt = int(65536.0/3000*expVolt+32768)
            dacCmd = str(dacVolt)+'\n'
            dacReply = '#INFO: DAC: '+str(dacVolt)
            for i in range(0, nSteps):
                ser.write(dacCmd.encode("UTF-8"))
                writeCmdLog(logFile, 'User', dacCmd, time=dt.datetime.today())
                if ser.in_waiting == 0:
                    print("Issue in voltage parameters protocol")
                    continue
                reply = ser.readline()
                if reply.rstrip().decode() == dacReply:
                    writeCmdLog(logFile, 'DStat', line.decode(),
                                time=dt.datetime.today())
                else:
                    print("Issue in voltage parameters protocol")
            print("Cleaning up leftovers")
            if ser.in_waiting > 0:
                replies = ser.read(ser.in_waiting)
                writeCmdLog(logFile, "DStat", replies.decode())
            # Write times
            for timePt in timeArray:
                timeCmd = str(timePt)+'\n'
                timeReply = '#INFO: Time: '+str(timePt)
                ser.write(timeCmd.encode("UTF-8"))
                writeCmdLog(logFile, 'User', timeCmd)
                reply = ser.readline()
                if line.rstrip().decode() == timeReply:
                    writeCmdLog(logFile, 'DStat', line.decode(),
                                time=dt.datetime.today())
                    continue
                else:
                    print('Issue in time parameter protocol')
            print("Cleaning up leftovers")
            if ser.in_waiting > 0:
                replies = ser.read(ser.in_waiting)
                writeCmdLog(logFile, "DStat", replies.decode())
            return True
        else:
            print('Failed to initialize experiment')
            return False
    except serial.SerialException:
        print("Problems with Serial Port, Parameters are not uploaded")
        return False


def resetDStat(ser):
    """Is supposed to reset the DStat, however, the function has not
    successfully done this."""
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
    """Function automatically converts current values from digital values to Amps

    VARIABLES:
    adcCode: Digital adc current value returned by the DStat
    Gain: INT. Gain value definied in user parameters. Do not use the actual value this
    corresponds to.
    pgaGain: Adjustable pgaGain if necessary. However, this should not need to be adjusted.
    Default value is 2.

    RETURNS: Float, corresponding to the current in Amps
    """
    # Assumes that PGA value is 2. Will need to edit otherwise.
    gainValues = {0: 1, 1: 100, 2: 3000, 3: 3E4, 4: 3E5, 5: 3E6, 6: 3E7,
                  7: 1E8}
    current = (float(adcCode)/(pgaGain/2))*(1.5/gainValues[gain]/8388607)
    return current


def runExperiment(ser, expLength, gain, expVolt, logFile=None,
                  dataFile='Test', rptTime=300,
                  timeFmtStr='%m/%d/%Y %H:%M:%S.%f'):
        """Runs the experiment, specifically, it runs the experiment
        initialization, and gathers data until the completion code is sent
        by the DStat.

        A new data file is created, in which the experimental parameters (voltage,
        start time, gain) are written, then the actual data written

        Data is append to the data file, contining the elapsed experimental time
        and the measured current at that time.

        Additionally, the script reports an averaged current in a user defined
        reporting time, though this averaging is NOT done to the raw data.

        The only thing this script will NOT catch is if the DStat stalls. If you are not
        receiving data on the report time specified, then you must reset the script.

        VARIABLES:
        ser: Serial port object for DStat
        expLength: Int. Experimental time in seconds
        gain: Int. Gain value corresponding to the table in the user params.
        expVolt: Experimental voltage, mV.
        logFile: String, command log file path
        rptTime: Float or int. Time for averaging current, this does not affect
        outputted data.
        timeFmtStr: String. Formatting string for times.

        RETURNS: Boolean for successful experimental completion.

        """
        expStart = initializeExperiment(ser, expLength, expVolt,
                                        logFile=logFile)
        if not expStart:
            print('Failed to initialize experiment, aborting')
            return False
        print('Experimental parameters uploaded')
        startTime = dt.datetime.today()
        # Create dataFile, check for copies and fix file name
        dataFile = fileNameCheck(dataFile)
        # Write experimental parameters to dataFile
        with open(dataFile, 'a') as outFile:
            dataWriter = csv.writer(outFile, dialect='excel')
            dataWriter.writerow(['Experimental start: ' +
                                startTime.strftime(timeFmtStr)])
            dataWriter.writerow(['Gain value: '+str(gainValues[gain])])
            dataWriter.writerow(['Experimental voltage: '+str(expVolt)+' mV'])
            dataWriter.writerow(['Elapsed Time (s)', 'Current (A)'])
        # Initialize averaging arrays
        currentVals = []
        timeVals = []
        rptTime = dt.timedelta(seconds=rptTime)
        checkTime = dt.datetime.today()
        interval = checkTime-startTime
        writeCmdLog(logFile, 'User', 'Experiment Start', timeFmt=timeFmtStr,
                    time=startTime)
        reply = ser.readline()
        print('Entering main experimental loop')
        # Run data collection until ending command is sent by the DStat
        while reply.rstrip() != b'@DONE':
            if ser.in_waiting == 0:
                time.sleep(0.1)
                # Don't want to try to readlines on empty serial port
                continue
            reply = ser.readline()
            if reply.startswith(b'#') or reply.startswith(b'@'):
                # Log informational messages and reports from DStat
                try:
                    writeCmdLog(logFile, 'DStat', reply.decode())
                except UnicodeDecodeError as e:
                        print(reply)
                        print(e)
                        print('Problematic reply from DStat not logged')
                        pass
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


timeFmtStr = '%m/%d/%Y %H:%M:%S.%f'
gainValues = {0: 1, 1: 100, 2: 3000, 3: 3E4, 4: 3E5, 5: 3E6, 6: 3E7,
              7: 1E8}
with initializeDStat(serialPort, logFile=logFile) as ser:
    # Ensures closure of port on failure or keyboard interrupt
    print('DStat Initialized')
    # Write the DStat version info to script
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
    if not exp:
        raise ExperimentalError("Initialization error")
