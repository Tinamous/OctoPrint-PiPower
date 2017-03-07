
import os
import time

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

temp_sensors = [('air','28-0000070e4078'), ('pcb','28-000007538f5b')]

def temp_raw(sensor):

    sensorPath = "/sys/bus/w1/devices/{}/w1_slave".format(sensor[1])
    f = open(sensorPath, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp(sensor):

    lines = temp_raw(sensor)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = temp_raw(sensor)

    temp_output = lines[1].find('t=')

    if temp_output != -1:
        temp_string = lines[1].strip()[temp_output+2:]
        temp_c = float(temp_string) / 1000.0
        return round(temp_c,1)

while True:
        message = ""
        for sensor in temp_sensors:
                message += "{}={},  ".format(sensor[0], read_temp(sensor))

        print (message)
        time.sleep(1)
