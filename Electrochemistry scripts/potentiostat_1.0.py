import sys
import serial, io
from serial.tools import list_ports
import time
import numpy as np
import struct
from struct import *
import numpy as np
import matplotlib.pyplot as plt
# note: dstat returns data in binary as hexadecimal, form \xhh (where hh = 2-value hex)


ex_time=60 ; #seconds
avg_time = 5 ##return averaged data over this time interval in seconds

#potentiostat voltage (mV)
ex_mV = -800

# dac gains: change this if current sensitivity to change is to high or too low as a function of resistance. 1 or 2 are good "general" numbers to start with. May see little change in current with large change in resistance at setting of "0"

ex_dac_gain = 1. ## set dac gain here. gain value of 2 is EG2, gain of 1 is EG1, etc
gain = 100 #!!!!Set this according to the table below (and value chosen for ex_dac_gain). e.g. "2" = 3k (set to 1 for zero ohms to avid division arrors)

            # gains allowed by dstat. use lowest value to detect (desired) differences in current
            #define POT_GAIN_0 0
            #define POT_GAIN_100 1
            #define POT_GAIN_3k 2
            #define POT_GAIN_30k 3
            #define POT_GAIN_300k 4
            #define POT_GAIN_3M 5
            #define POT_GAIN_30M 6
            #define POT_GAIN_100M 7




# genereally DO NOT need to change these
adc_gain=2 # this is generally held at 2
gain_trim = 0  # leave at 0 for now





#open serial port. may need to change port value
ser = serial.Serial('/dev/tty.usbmodem1411',baudrate=19200, timeout=1)
ser.isOpen()
ser.flushOutput()
ser.flushInput()


#test connection (put exception for no connection here, eventually)

ser.write(b'!0\n'); time.sleep(0.3)
ser.write(b'V\n'); time.sleep(0.3)


for line in ser:
    
    if line==(b'@DONE\n'):
        print ("finished")
        break
    if line==(b'@RCV 0\n'):
        print ("communication ok")
        time.sleep(1)
        break        


# set initial parameters
#adc setting--          (example: EA2 03 1 \n == PGA2x, sample rate 2.5 hz, buffer on)
# NORMAL SETTING FOR ADC gain is 2 (2x)
ser.write(b'!9\n'); time.sleep(0.3); ser.write(b'EA%d 03 1 \n'%adc_gain);time.sleep(0.3)


for line in ser:
    print (line)
    if line==(b'@DONE\n'):
        
        print ("finished with")
        break
print ("EA section")




ser.write(b'!6\n'); time.sleep(0.3); ser.write(b'EG%d 0 \n'%ex_dac_gain);time.sleep(0.3) 

for line in ser:
    print (line)
    if line==(b'@DONE\n'):
        print ("finished with")
        break
print ("EG section")

time.sleep(0.3)





output = [(),()]

dac_mV = int(21846*(ex_mV/1000)+32768)


########## run experiment- chronoamperometry (fre 1-1000)
#1E=experiment, 2R = chronoamperometry,3 number of potential steps, 4 keep at 0) 
ser.write(b'!6\n');time.sleep(0.1); ser.write(b'ER1 0\n'); time.sleep(0.1)


ser.write(b'%d\n'%dac_mV); time.sleep(0.1);
ser.write(b'%d\n' % ex_time); time.sleep(0.1)

plt.ion() # allow interactive plot

first_timepoint=avg_time
currsum=([])
tpoints=0
tpointsa=([])
q=[]
xvals=([0])
yvals=([0])
xmin=([0])
xmax=([0])
ymin=([])
ymax=([])
millisec = 1e-10
sec = 1e-10

stderrlist = ([0])
f = open('test.dat', 'a')
f.write('\n\nStart run.......     time-curr-sd-points     ###########################################################')
f.close



while True:

    for line in ser:

        data = ser.read(10)
            
        if data.startswith(b'B'):

            x = data.replace(b'B\n',b'')
            new = struct.unpack('<HHl', x)
            sec, millisec,curr = new
            float(sec); float(millisec); float(curr)
            # print (sec,millisec,curr)
            exptime = (sec+(millisec/1000.))
            current = (curr)*(adc_gain/2)*(1.5/gain/8388607)
            currsum.append(current)
            #print (currsum)

            if exptime>=first_timepoint:
            
                print ("%d seconds reached. recording averaged"%exptime)
                time_average = (exptime-(avg_time/2))
                mean_current = np.mean(currsum)
                sd_current=np.std(currsum)
                tpointsa=len(currsum)
                print("time:", time_average)
                print("current:", mean_current)
                print("standard_deviation:", sd_current)
                print("number of points:", tpointsa)
                z = [(time_average),(mean_current),(sd_current),(tpointsa)]
                q.append(z)

                
                #write data to file
                print ("writing data to file")
                f = open('test.dat', 'a')
                f.write('\n')
                f.write(str(z))
                f.close
                
                xvals.append(time_average)
                yvals.append(mean_current)
                stderrlist.append(sd_current)

 
                first_timepoint=exptime+avg_time

                xmin=min(xvals); xmax=max(xvals)
                ymin=min(yvals); ymax=max(yvals)
                axes = plt.gca()
                axes.set_xlim([xmin,xmax])
                axes.set_ylim([ymin,ymax])
                plt.errorbar(xvals, yvals, yerr=stderrlist, fmt='o')
                plt.pause(0.05)

                currsum=[]

            

##            k = ser.inWaiting()
##            if k > 1:
##                print ("warning: problem reading all data in buffer...%d unread bytes between databpoints recorded.\n Try decreasing collection rate or turn off printing/real-time graphing" %k)


    print ("writing final data to file")
    f = open('test.dat', 'a')
    f.write('End of run ####################################################')
    f.close

    
    
    ser.close()
    print ("\n\nMeasurements terminated normally after %d seconds. Goodbye..."%exptime)
    
    while True:

        plt.show(0.05)


    



























