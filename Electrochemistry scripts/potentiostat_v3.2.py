#no resetting of port(s); this script attempts to send a periodic 'abort' command to potentiostat, halting data collection but leaving port open. 

""" TO DO LIST:

1) Code linting
2) Figure out issues with crashing
3) Structure output better for ease of analysis
4) Write to log on crash
5) Change date formatting to human readable"""

import sys
import serial, io
from serial.tools import list_ports
import time
import numpy as np
import struct
from struct import *
import numpy as np
#import matplotlib.pyplot as plt
from datetime import datetime
import warnings; warnings.filterwarnings("ignore",".*GUI is implemented.*")
import pykush
from pykush import *
import signal
import os
import smtplib
import ctypes


#name of experiment
exp_name='Redoxotron_4'


#### global variables.....change these

#interval over which data is averaged (sec)
avg_time = 30 ## 600 = 10 min


#potentiostat voltage (mV)
ex_mV = 1000

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




# generally DO NOT need to change these
adc_gain=2 # this is generally held at 2
gain_trim = 0  # leave at 0 for now

#only change these if experiment end is desired
ex_time=50200#length of run. set to value greater than refresh_freq for running infinite loop...25200 = 7 hours
refresh_freq =  28800#potentiostat refresh frequency in seconds 3600=1 hr, 14400 = 4 hours

# countdown interval

countdownint=10


#close port with refresh. set "true" if abort attempt is coupled with port closure

use_port_refresh=True
send_text=False


recievers=['6178996990@txt.att.net']



#plotting axis global vars
xvals=[()]
yvals=[()]
stderrlist=[()]



def open_port(ser):

    try:

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(10)


        if ser.is_open==True:
            ser.close()

        if ser.is_open==False:

                #open serial port. may need to change port value
                ser = serial.Serial('/dev/ttyACM0', rtscts=True, timeout=3)
                signal.alarm(0)
                print("ACM0 succesfully opened. writing experimental parameters")
                write_params(ser)
                
                return ser

        else:
            print("port already open...")

        
        
    except:
        print("could not open port on ACM0, closing port and re-trying after port enumeration")

        if ser.is_open==True:
            ser.close()
        signal.alarm(0)
        power_cycle()
        time.sleep(2)
        open_port(ser)



def write_params(ser):


        signal.signal(signal.SIGALRM, handler)
        signal.alarm(30)


        ser.write(b'!0\n'); time.sleep(0.3)
        ser.write(b'V\n'); time.sleep(0.3)
##
##
##        for line in ser:
##            print(line)
##            if line==(b'@DONE\n'):
##                print ("finished")
##                break
##            if line==(b'@RCV 0\n'):
##                print ("communication ok")
##                time.sleep(0.5)
##                break
            
        dac_mV = int(21846*(ex_mV/1000)+32768)

        
        ser.write(b'!9\n'); time.sleep(1); ser.write(b'EA2 03 1\n');time.sleep(1) #if changing gain, check number of characters to send

##        for line in ser:
##            print (line)
##            if line==(b'@DONE\n'):
##                
##                print ("finished with")
##                break
##        print ("EA section")
##


        ser.write(b'!5\n'); time.sleep(1); ser.write(b'EG1 0\n');time.sleep(1) 
##
##        for line in ser:
##            print (line)
##            if line==(b'@DONE\n'):
##                print ("finished with")
##                break
##        print ("EG section")


        ser.write(b'!5\n');time.sleep(1); ser.write(b'ER1 0\n'); time.sleep(1)
        ser.write(b'%d\n'%dac_mV); time.sleep(1);
##
##        for line in ser:
##            print (line)
##            if line==(b'@DONE\n'):
##                print ("finished with")
##                break
##        print ("ER section")
        ser.write(b'%d\n' % ex_time); time.sleep(1)


        print("\nparameters successfully uploaded....")

        if ser.is_open==True:
            print("port still open after writing params, continuing to data collection loop...\n")

        else:
            print('problem with serial port, attempting to reset port')
            signal.alarm(0)
            open_port()

        signal.alarm(0)
        return ser




def power_cycle():

        signal.signal(signal.SIGALRM, handler_exit)
        signal.alarm(20)
        
       #power cycle potentiostat
        print("power cycling potentiostat")
        yk = pykush.YKUSH()
        #print (yk)
        yk.set_allports_state_down()
        #print(yk);
        time.sleep(5)
        yk.set_allports_state_up()
        time.sleep(5)
        print("power cycling complete\n")
        signal.alarm(0)


def handler(signum, frame):
    global textmessage
    print('Signal handler called with signal', signum)
    print('Unknown problem opening port or writing parameters to potentiostat. trying power-cycle to fix problem...'); time.sleep(1)

    if textmessage == False:

        gmail_pass = 'Rawegg99!'
        gmail_address='kocar.potentiostat@gmail.com'
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_address, gmail_pass)
        server.sendmail(gmail_address,recievers, 'potentiostat timed out somewhere. Refresh loop initiated...')

    textmessage = True
    server.quit()


    power_cycle()
    open_port()
    return


def handler_exit(signum, frame):
    print('Signal handler called with signal', signum)
    print('strange problem communicating with YKUSH USB power cycler. Escaping to main loop and attempting reset....'); time.sleep(1)
    power_cycle()
    open_port()
    return
    

def data_collection(loopnumber, start_time, ser, refresh_time, looptime, exptime, collection_countdown):

    timeold=0
    currsum=[]
    global textmessage
    g=avg_time+30
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(g)

    try:
    

        try:
            
            if textmessage ==True:
                
                gmail_pass = 'Rawegg99!'
                gmail_address='kocar.potentiostat@gmail.com'
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(gmail_address, gmail_pass)
                server.sendmail(gmail_address,recievers, 'data collection successfully resumed after resetting potentiostat')
                textmessage = False
                server.quit()
                    
        except:
            print("error sending text message")
            textmessage = False
            pass

        ser.flushOutput()
        ser.flushInput()

        for line in ser:
            
            signal.alarm(g)
            time_now=time.time()
            data = ser.read(ser.inWaiting())
            #print(data)
            
            if data.startswith(b'@') or data.startswith(b'#') or data.startswith(b'\n'): # note: dstat returns data in binary as hexadecimal, form \xhh (where hh = 2-value hex)
                pass

            else:
                try:

                    x = data.replace(b'\n',b'')
                    new = struct.unpack('<HHl', x)
                    sec, millisec,curr = new
                    float(sec); float(millisec); float(curr)
                    exptime = (sec+(millisec/1000.))
                    current = (curr)*(adc_gain/2)*(1.5/gain/8388607)
                    currsum.append(current)
                    print(current)

                except:

                    print("ignoring nondata line")
                    pass
                

            if time_now>=collection_countdown:

                #track time and update data matrix when experimental time exceeds specified timeloop
                    exptime_int=int(exptime)

                    if exptime_int!=0:

                        print ("\n%d seconds reached in data collection loop. recording averages from data point %d"% (exptime,loopnumber))
                        
                        if exptime < (avg_time/2):
                            time_average_exp=time_now
                        else:
                            time_average_exp = (time_now-(avg_time/2))

                        mean_current = np.mean(currsum)
                        sd_current=np.std(currsum)
                        tpointsa=len(currsum)
                        print("time:", time_average_exp)
                        print("current:", mean_current)
                        print("standard_deviation:", sd_current)
                        print("number of points:", tpointsa)
                        z = [(time_average_exp),(mean_current),(sd_current),(tpointsa)]
                        
                        #write data to file
                        print ("writing data to file\n")
                        f = open('test.dat', 'a')
                        time.sleep(0.5)
                        f.write('\n')
                        f.write(str(z))
                        f.close
                        time.sleep(0.5)
                        
                        currsum=[]
                        collection_countdown=time_now+avg_time
                        loopnumber+=1
                        time.sleep(0.5)
                            
                           
                       
            if time_now >=looptime: #potentiostat refresh when "refresh frequency" exceeded by timeloop

                print("\npotentiostat refresh, breaking data collection loop")
                ser.close()
                signal.alarm(0)
                return(loopnumber, ser)
            
            signal.alarm(0)


    except:
        
        print("\nproblem with data collection loop. Will attempt to reset potentiostat\n")
        
        if ser.is_open==True:
            ser.close()

        if textmessage == False:
            
            gmail_pass = 'Rawegg99!'
            gmail_address='kocar.potentiostat@gmail.com'
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_address, gmail_pass)
            server.sendmail(gmail_address,recievers, 'potentiostat failed to refresh in data loop')
            textmessage = True
            server.quit()
        
        return(loopnumber,ser)

        textmessage = True

def main():
    

    pot_refresh_time=0.
    exptime=0
    refresh_time=avg_time
    ser=serial.Serial(port=None)
    time_average=0
    time_average_exp=0
    start_time=time.time()
    time_now=time.time()
    collection_countdown=time_now+avg_time
    loopnumber=1
    refresh_time=time_now+refresh_freq


    f = open('test.dat', 'a')
    f.write('\n\n\ndate,exp name, mV, dac_gain value, actual dac gain, adc_gain, adc_gain_trim, ex_time, avg_time, refresh_freq\n')
    f.write('%s,%s, %d, %d, %d, %d, %d, %d, %d, %d'%(time_now,exp_name,ex_mV,ex_dac_gain,gain,adc_gain,gain_trim,ex_time,avg_time,refresh_freq))
    f.write('\n\n\nStart run.......     time-curr-sd-points     ###########################################################')
    f.close

    init_flag=0

    global textmessage
    textmessage = False
    
    while True:

        try:

            if ser.is_open==True:
                ser.close()

            if ser.is_open==False:
                power_cycle()
                ser=open_port(ser)
                time.sleep(0.1)
            
            time_now=time.time()
            looptime=time_now+refresh_freq
            loopnumber, ser=data_collection(loopnumber, start_time,ser, refresh_time, looptime, exptime, collection_countdown)

            if use_port_refresh==True:
                print("refreshing potentiostat through power cycling")


        except:


            print("problem in main program loop. attempting to clear variables and reset")
            power_cycle()    
            pot_refresh_time=0.
            exptime=0
            refresh_time=avg_time
            time_average=0
            time_average_exp=0
            start_time=time.time()
            time_now=time.time()
            collection_countdown=time_now+avg_time
            loopnumber=1
            refresh_time=time_now+refresh_freq
            ser=serial.Serial(port=None)
            time.sleep(1)
            print("reset complete...restarting entire loop, including power cycle")
            time.sleep(1)
            
            if textmessage == False:
                gmail_pass = 'Rawegg99!'
                gmail_address='kocar.potentiostat@gmail.com'
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(gmail_address, gmail_pass)
                server.sendmail(gmail_address,recievers, 'potentiostat failed to refresh in mainloop')
                
                server.quit()
                    
            textmessage = True
            
            pass
        



if __name__ == "__main__":
              main()





