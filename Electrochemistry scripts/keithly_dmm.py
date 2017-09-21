import visa
import time
import numpy as np
import matplotlib.pyplot as plt
import usbtmc

#note:  Power-cycle keithley prior to re-starting long experiment...
# Run this program as root (sudo idle3) or it probably won't work!

rm = visa.ResourceManager('@py')
print(rm.list_resources())
keithley = rm.open_resource('USB0::1510::8448::8004460::0::INSTR')
keithley.write('*cls')
time.sleep(1)
keithley.write('*rst')
time.sleep(1)

#Change this stuff......############################################

#plot voltage data in real-time?
plotvolt=True

#print measurements in loop

loopvals=True

#choose measurements (set to True to enable measurement).

number_of_measurement_types=1
resistancemeas=False
currentmeas=False
voltagemeas=True

#set interval for countdown timer (seconds) 30

countdown_timer=5 #Seconds

#experiment time  36000 (total seconds...set to ridiculously high number--like 999999999999 if you don't know, then just terminate program when done (remember to power-cycle keithley)

totaltime=3600 #Seconds

#seconds between measurements (long times?) 1800
tCycles = 15
#number of measurements at each point
numpoints = 5
#pause (in seconds) between measurements. use value of 0.05 or greater to ensure stable measurements
pauseMeasure=0.2


# exits program if data collection time exceeds time between measurements

estMeasTime = ((pauseMeasure+1.25)*number_of_measurement_types*numpoints)+6 #multiplied by 3 = fudge factor
print ("data collection time is guessed to be %d seconds, time between datapoints is %d seconds"%(estMeasTime, tCycles))
if tCycles >= estMeasTime:
    print ("data collection scheme ok, starting in 5 seconds")
    time.sleep(5)

else:
    print("not enough time to collect %d measurments between %d second intervals \n"%(numpoints,tCycles))
    print("increase seconds between measurements or lower number of replicates per point \n")
    print("closing in 5 seconds....")
    time.sleep(5)
    print("Exiting with error. goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()


#don't change anything from here on.......#################################
floattime=time.time()
initialtime=time.time()
resistance=[()]
voltage=[()]
current=[()]


time.sleep(2)
print ("initial test measurement...")

voltage = keithley.query("measure:voltage:dc?")
if voltage == "":
    print ("problem with Keithley. Stopping program in 5 seconds. ")
    print ("power cycle Keithly and re-start program")
    time.sleep(5)
    print("Exiting with error. goodbye....")
    keithley.write('system:local')
    keithley.close()
    exit()

print ("equipment ok, starting data collection\n")
time.sleep(2)

print ("starting initial measurement\n")
time.sleep(1)


measurenum=0

voltoutput=[(),(),()]
tempvals=[(0)]
v=[(),(),()]
c=[(),(),()]
r=[(),(),()]
q=[]

#declare plotting variables

plot_initime=time.time()
xvals = ([0])
yvals = ([0])
stderrlist = ([0])
xmin = ([0])
ymin = ([0])
ymax = ([0])

plt.ion()

while True:

    
    if measurenum==0 or time.time()>=floattime:
        
        floattime=time.time()+tCycles
        currtime=time.asctime(time.localtime(time.time()))
        currtimeplain=time.time()

        if voltagemeas==True:
            
            print ('\nvoltage measurement number: %d'%measurenum)
            print ('measurement time: %s'%time.asctime(time.localtime(time.time())))
            print ('starting voltage measurements')
            
            for i in range(numpoints):            
                voltemp = keithley.query("measure:voltage:dc?")
                voltemp2 = voltemp.replace("\n","")
                try:
                    voltage = float(voltemp2)
                    tempvals.append(voltage)
                except:
                    print("exception: problem reading instrument, or non-float value returned. data not recorded")
                    
                if loopvals ==True:
                    try:
                        print ("reading#%d: %f"%(i,voltage))
                    except:
                        print("exception: cannot print non-float value")
                time.sleep(pauseMeasure)
            voltage_average=np.mean(tempvals)
            voltage_sd=np.std(tempvals)
            voltage_numpoints=numpoints
            print("\n")
            print (time.asctime(time.localtime(time.time())))
            print ("average of %d points is %f volts, with standard deviation of %f volts\n"%(voltage_numpoints,voltage_average,voltage_sd))
            v = [(voltage_numpoints),(voltage_average),(voltage_sd)]
            tempvals=[(0)]
            time.sleep(2)
            
        if currentmeas==True:
            
            print ('\n\ncurrent measurement number: %d'%measurenum)
            print ('measurement time: %s'%time.asctime(time.localtime(time.time())))
            print ('starting current measurements')
            
            for i in range(numpoints):

                currentemp = keithley.query("measure:current:dc?")
                currentemp2=currentemp.replace("\n","")
                
                try:
                    current = float(currenttemp2)
                    tempvals.append(current)
                except:
                    print("exception: problem reading instrument, or non-float value returned. data not recorded")
                          
                if loopvals ==True:
                    try:
                        print ("reading#%d: %f"%(i,current))
                    except:
                        print("exception: cannot print non-float value")
                time.sleep(pauseMeasure)
                
            current_average=np.mean(tempvals)
            current_sd=np.std(tempvals)
            current_numpoints=numpoints
            print("\n")
            print (time.asctime(time.localtime(time.time())))
            print ("average of %d points is %f amps, with standard deviation of %f amps\n"%(current_numpoints,current_average,current_sd))
            c = [(current_numpoints),(current_average),(current_sd)]
            tempvals=[(0)]
            time.sleep(2)
            
        if resistancemeas==True:
            
            print ('\n\nresistance measurement number: %d'%measurenum)
            print ('measurement time: %s'%time.asctime(time.localtime(time.time())))
            print ('starting resistance measurements')
            
            for i in range(numpoints):

                resistancetemp = keithley.query("measure:resistance?")
                resistancetemp2 = resistancetemp.replace("\n","")
                try:
                    resistance = float(resistancetemp2)
                    tempvals.append(resistance)
                except:
                    print("exception: problem reading instrument, or non-float value returned. data not recorded")
                if loopvals ==True:
                    try:
                        print ("reading#%d: %f"%(i,resistance))
                    except:
                        print("exception: cannot print non-float value")
                time.sleep(pauseMeasure)
            resist_average=np.mean(tempvals)
            resist_sd=np.std(tempvals)
            resist_numpoints=numpoints
            print("\n")
            print (time.asctime(time.localtime(time.time())))
            print ("average of %d points is %f ohms, with standard deviation of %f ohms\n\n"%(resist_numpoints,resist_average,resist_sd))
            r = [(resist_numpoints),(resist_average),(resist_sd)]
            tempvals=[(0)]
            time.sleep(2)
 
            
        measurenum+=1
        newvals=[(currtime),(floattime),(v),(c),(r)]
        #q.append(newvals)
        #print (q)
        print ("\n\n\nwriting data to file...")
        f = open('dmm.dat','a')
        f.write('\n')
        f.write(str(newvals))
        f.close
        print("done writing to file...")
        thisround=((time.time())-currtimeplain)
        print("all measurements required a total of %f seconds\n"%thisround)
        newround = (floattime-(time.time()))
        print("%d seconds until next round of measurements"%newround)
        countdown= newround-countdown_timer

        ##plot voltage values as they come in

        if plotvolt==True:
            plottime=(time.time())-(plot_initime)
            xvals.append(plottime)
            yvals.append(voltage_average)
            stderrlist.append(voltage_sd)


            xmin=min(xvals); xmax = max(xvals)
            ymin=(min(yvals)-((max(stderrlist))*2)); ymax = (max(yvals)+((max(stderrlist))*2))
            axes = plt.gca()
            axes.set_xlim([xmin, xmax])
            axes.set_ylim([ymin, ymax])
            plt.errorbar(xvals, yvals, yerr=stderrlist, fmt='o')
            plt.pause(0.05)

            
        
    

    elif time.time()>=initialtime+totaltime:
        break

    elif floattime-time.time()<=countdown:
        endtime=(initialtime+totaltime)-(time.time())
        print ("%d seconds before next measurement, and %d seconds before end of experiment"%(countdown, endtime))
        countdown-=countdown_timer

print ("elapsed time: %f seconds"%(floattime-initialtime))
print("normal exit. goodbye....")
keithley.write('system:local')
keithley.close()

while True:
    plt.pause(0.05)
        



