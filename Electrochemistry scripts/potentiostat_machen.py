"""
TO DO LIST:
1) Rewrite major functionality
    a) Write parameters to dstat and file
    b) Start experiment
    c) Read in data
    d) Output data to some type of file
2) Implement clean exits for serial ports
3) Implement logging of errors and commands

ERRORS:
1) Reset DStat doesn't work period.
2) Port search also does not seem to work, get serial exceptions where port appears to already be in use.
"""

import serial
import time
import numpy as np
import datetime as dt
import signal
import pandas as pd


# Name of experiment: What does this mean? Think it's for the dstat
exp_name = 'Redoxotron_4'
# Name of file to write to
fileName = 'Redoxotron4.dat'


# Global Variables: User edited

# Interval over which data is averaged (sec)
avg_time = 30  # 600 = 10 min


# Potentiostat voltage (mV)
ex_mV = 1000

"""dac gains: change this if current sensitivity to change is to high or too
low as a function of resistance.
1 or 2 are good "general" numbers to start with. May see little change in
current with large change in resistance at setting of "0"""

ex_dac_gain = 1.  # Set dac gain here. gain value of 2 is EG2, gain of 1 is EG1
gain = 100

"""!!!!Set this according to the table below
(and value chosen for ex_dac_gain).
e.g. "2" = 3k (set to 1 for zero ohms to avid division arrors)

    #gains allowed by dstat. use lowest value to detect targeted current diffs
    #define POT_GAIN_0 0
    #define POT_GAIN_100 1
    #define POT_GAIN_3k 2
    #define POT_GAIN_30k 3
    #define POT_GAIN_300k 4
    #define POT_GAIN_3M 5
    #define POT_GAIN_30M 6
    #define POT_GAIN_100M 7
"""


# generally DO NOT need to change these
adc_gain = 2  # This is generally held at 2
gain_trim = 0  # Leave at 0 for now

# Only change these if experiment end is desired
ex_time = 50200  # length of run in seconds
# Set ex_time to value greater than refresh_freq for running infinite loop
refresh_freq = 28800  # Potentiostat refresh frequency in seconds

# countdown interval, not used apparently

countdownint = 10


# Close port with refresh.
# Set "true" if abort attempt is coupled with port closure

use_port_refresh = True

# Plotting axis global vars
xvals = [()]
yvals = [()]
stderrlist = [()]


class Error(Exception):
    """ Base class for exceptions. """
    pass


class CommunicationsError(Error):
    """Error class for failed communications to dstat"""
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def writeCmdLog(logFile, type, cmd, timeFmt='%m/%d/%Y %H:%M%S.%f',
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
        elif line.rstrip() is b'@DONE':
            writeCmdLog(logFile, 'DStat', line.decode(), time=time)
            return True  # If command completes, returns True
        else:
            print('Unexpected Response from DStat, Check Log')
            writeCmdLog(logFile, 'DStat', line.decode(), time=time)
    return False  # Should give a "fail" state if the @DONE reply is not recieved


def setDStatParams(ser, gain=2, logFile=None):
    try:
        # Try set adc
        adcSet = sendCommand(ser, 'EA2 A1 1')  # No need to change ADC settings
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


logFile = 'CommandLog.log'
serialPort = '/dev/ttyACM0'
timeFmtStr = '%m/%d/%Y %H:%M%S.%f'
with initializeDStat(serialPort, logFile=logFile) as ser:
    sendCommand(ser, 'V')
    print(ser.readlines())
    adcSet, gainSet = setDStatParams(ser, gain=2, logFile=logFile)
    print((adcSet, gainSet))

# def write_params(ser):
#         signal.signal(signal.SIGALRM, handler)
#         signal.alarm(30)
#         ser.write(b'!0\n')
#         time.sleep(0.3)
#         ser.write(b'V\n')
#         time.sleep(0.3)
# #        for line in ser:
# #            print(line)
# #            if line==(b'@DONE\n'):
# #                print ("finished")
# #                break
# #            if line==(b'@RCV 0\n'):
# #                print ("communication ok")
# #                time.sleep(0.5)
# #                break
#         dac_mV = int(21846*(ex_mV/1000)+32768)
#         ser.write(b'!9\n')
#         time.sleep(1)
#         ser.write(b'EA2 03 1\n')
#         time.sleep(1)
# # If changing gain, check number of characters to send
# #        for line in ser:
# #            print (line)
# #            if line==(b'@DONE\n'):
# #                print ("finished with")
# #                break
# #        print ("EA section")
# #
#         ser.write(b'!5\n')
#         time.sleep(1)
#         ser.write(b'EG1 0\n')
#         time.sleep(1)
# #
# #        for line in ser:
# #            print (line)
# #            if line==(b'@DONE\n'):
# #                print ("finished with")
# #                break
# #        print ("EG section")
#         ser.write(b'!5\n')
#         time.sleep(1)
#         ser.write(b'ER1 0\n')
#         time.sleep(1)
#         ser.write(b'%d\n' % dac_mV)
#         time.sleep(1)
# #
# #        for line in ser:
# #            print (line)
# #            if line==(b'@DONE\n'):
# #                print ("finished with")
# #                break
# #        print ("ER section")
#         ser.write(b'%d\n' % ex_time)
#         time.sleep(1)
#         print("\nparameters successfully uploaded....")

#         if ser.is_open:
#             print("port still open after writing params," +
#                   " continuing to data collection loop...\n")
#         else:
#             print('problem with serial port, attempting to reset port')
#             signal.alarm(0)
#             open_port()

#         signal.alarm(0)
#         return ser

# def data_collection(loopnumber, start_time, ser, refresh_time, looptime,
#                     exptime, collection_countdown):

#     timeold = 0  # What is this?
#     currsum = []
#     global textmessage
#     g = avg_time+30
#     signal.signal(signal.SIGALRM, handler)
#     signal.alarm(g)

#     try:
#         ser.flushOutput()
#         ser.flushInput()

#         for line in ser:
#             signal.alarm(g)
#             time_now = time.time()
#             data = ser.read(ser.inWaiting())
#             # print(data)
#             if data.startswith(b'@') or data.startswith(b'#') or \
#                data.startswith(b'\n'):
#                 # note: dstat returns data in binary as hexadecimal,
#                 # form \xhh (where hh = 2-value hex)
#                 pass

#             else:
#                 try:
#                     x = data.replace(b'\n', b'')
#                     new = struct.unpack('<HHl', x)
#                     sec, millisec, curr = new
#                     float(sec)
#                     float(millisec)
#                     float(curr)
#                     exptime = (sec+(millisec/1000.))
#                     current = (curr)*(adc_gain/2)*(1.5/gain/8388607)
#                     currsum.append(current)
#                     print(current)

#                 except:

#                     print("ignoring nondata line")
#                     pass

#             if time_now >= collection_countdown:

#                 """ track time and update data matrix when
#                     experimental time exceeds specified timeloop"""
#                 exptime_int = int(exptime)

#                 if exptime_int != 0:
#                     fmtExpTime = datetime.datetime\
#                                  .fromtimestamp(exptime).strftime('%c')
#                     print("""\n{0} seconds reached in data collection loop.
#                            Recording averages from
#                             data point {1}""".format(fmtExpTime,
#                                                      loopnumber))
#                     if exptime < (avg_time/2):
#                         time_average_exp = time_now
#                     else:
#                         time_average_exp = (time_now-(avg_time/2))

#                     mean_current = np.mean(currsum)
#                     sd_current = np.std(currsum)
#                     tpointsa = len(currsum)
#                     fmtAvgTime = datetime.datetime\
#                                  .fromtimestamp(time_average_exp)\
#                                  .strftime('%c')
#                     print("time:", fmtAvgTime)
#                     print("current:", mean_current)
#                     print("standard_deviation:", sd_current)
#                     print("number of points:", tpointsa)
#                     zPD = pd.DataFrame([mean_current, sd_current,
#                                         tpointsa], index=fmtAvgTime)
#                     print("Writing data to file\n")
#                     try:
#                         with open(exp_name+'.csv', 'a') as f:
#                             zPD.to_csv(f, header=False)
#                     except FileNotFoundError:
#                         print('No pandas file, creating new file.\n')
#                         zPD.index.name = 'Avg Meas Time'
#                         zPD.columns = ['AvgCurrent (A)', 'StdCurrent(A)',
#                                        'NPoints']
#                         zPD.to_csv(exp_name+'.csv')
#                     except:
#                         print('Unable to write pandas file.\n')

#                     z = [(time_average_exp), (mean_current),
#                          (sd_current), (tpointsa)]
#                     # Write data to file
#                     f = open(fileName, 'a')
#                     time.sleep(0.5)
#                     f.write('\n')
#                     f.write(str(z))
#                     f.close
#                     time.sleep(0.5)
#                     currsum = []
#                     collection_countdown = time_now+avg_time
#                     loopnumber += 1
#                     time.sleep(0.5)
#             if time_now >= looptime:
#                 # Potentiostat refresh when "refresh frequency" exceeded
#                 print("\npotentiostat refresh, breaking data collection loop")
#                 ser.close()
#                 signal.alarm(0)
#                 return(loopnumber, ser)
#             signal.alarm(0)
#     except:
#         print("\nproblem with data collection loop. Will attempt to reset potentiostat\n")
#         if ser.is_open:
#             ser.close()
#         return(loopnumber, ser)

# def main():
#     pot_refresh_time = 0.
#     exptime = 0
#     refresh_time = avg_time
#     ser = serial.Serial(port=None)
#     time_average = 0
#     time_average_exp = 0
#     start_time = time.time()
#     time_now = time.time()
#     collection_countdown = time_now+avg_time
#     loopnumber = 1
#     refresh_time = time_now+refresh_freq
#     f = open(fileName, 'a')
#     f.write('\n\n\ndate,exp name, mV, dac_gain value, actual dac gain, adc_gain, adc_gain_trim, ex_time, avg_time, refresh_freq\n')
#     f.write('%s,%s, %d, %d, %d, %d, %d, %d, %d, %d'%(time_now,exp_name,ex_mV,ex_dac_gain,gain,adc_gain,gain_trim,ex_time,avg_time,refresh_freq))
#     f.write('\n\n\nStart run.......     time-curr-sd-points     ###########################################################')
#     f.close()

#     init_flag = 0  # What does this do?
#     while True:
#         try:
#             if ser.is_open:
#                 ser.close()
#             if not ser.is_open:
#                 ser = open_port(ser)
#                 time.sleep(0.1)
#             time_now = time.time()
#             looptime = time_now+refresh_freq
#             loopnumber, ser = data_collection(loopnumber, start_time,
#                                               ser, refresh_time, looptime,
#                                               exptime, collection_countdown)
#             if use_port_refresh:
#                 print("refreshing potentiostat through power cycling")
#         except:
#             print("problem in main program loop." +
#                   " attempting to clear variables and reset")
#             pot_refresh_time = 0.
#             exptime = 0
#             refresh_time = avg_time
#             time_average = 0
#             time_average_exp = 0
#             start_time = time.time()
#             time_now = time.time()
#             collection_countdown = time_now+avg_time
#             loopnumber = 1
#             refresh_time = time_now+refresh_freq
#             ser = serial.Serial(port=None)
#             time.sleep(1)
#             print("reset complete...restarting entire loop, power cycle")
#             time.sleep(1)
#             pass


# if __name__ == "__main__":
#                 main()
