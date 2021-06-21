#!/bin/bash
# Import builtin packages
import logging
import os
import time
import argparse
import json

# Import installed packages
import RPi.GPIO as GPIO

# Import drivers
from INA260_MINIMAL import INA260
from EC25_Driver import smsModem
from RTC_SDL_DS3231 import SDL_DS3231


# ds3231 Registers
SECONDS_REG = 0x00
ALARM1_SECONDS_REG = 0x07
CONTROL_REG = 0x0E
STATUS_REG = 0x0F

# Pi Zero Pin Definitions
FLOAT = 17
BUTTON = 27
LED = 22

# 3G LTE Modem Pin Definitions 
RI = 6
DTR = 13
W_DISABLE = 19
PERST = 26

# argument parser
parser = argparse.ArgumentParser(description='Emulation mode?')
parser.add_argument('-emulation',dest='emulation',default='False',help='Emulation mode wont send sms')
parsed_args = parser.parse_args()

"""
##----------ds3231 Commands----------##
"""
def int_to_bcd(x):
    return int(str(x)[-2:], 0x10)

def write_time_to_clock(pos, hours, minutes, seconds):
    ds3231._write(pos, int_to_bcd(seconds))
    ds3231._write(pos + 1, int_to_bcd(minutes))
    ds3231._write(pos +2, int_to_bcd(hours))

def set_alarm1_mask_bits(bits):
    pos = ALARM1_SECONDS_REG
    for bit in reversed(bits):
        reg = ds3231._read(pos)
        if bit:
            reg = reg | 0x80
        else:
            reg = reg & 0x7F
        ds3231._write(pos, reg)
        pos = pos + 1

def enable_alarm1():
    reg = ds3231._read(CONTROL_REG)
    ds3231._write(CONTROL_REG, reg | 0x05)

def clear_alarm1_flag():
    reg = ds3231._read(STATUS_REG)
    ds3231._write(STATUS_REG, reg & 0xFE)

def check_alarm1_triggered():
    return ds3231._read(STATUS_REG) & 0x01 != 0

def set_timer(hours, minutes, seconds):
    # read clock time
    clock_time = ds3231.read_all()
    # set the alarm to be time + desired timer duration
    write_time_to_clock(ALARM1_SECONDS_REG, clock_time[4]+hours, clock_time[5]+minutes, clock_time[6]+seconds)
    # need to set some flags
    set_alarm1_mask_bits((True, False, False, False))
    enable_alarm1()
    clear_alarm1_flag()

def update_pi_time():
    print("Raspberry Pi=\t" + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Ds3231=\t\t%s" % ds3231.read_datetime())
    # ds3231.write_now()
    # print("Ds3231=\t\t%s" % ds3231.read_datetime())

    os.system('sudo date -s "%s"' % ds3231.read_datetime())

    print("Raspberry Pi=\t" + time.strftime("%Y-%m-%d %H:%M:%S"))

"""
##----------Commands for settings file----------##
"""
# Function to load in settings from a json file
def load_settings():
	# Open the setting file and read in the data
	with open('settings_.json') as json_file:
		settings = json.load(json_file)
	# Check the data for for required settings 
	for s in settings['settings']:
		ID = str(s['ID'])
		NUM = str(s['NUM'])
		logging.info('ID loaded: ' + s['ID'])
		logging.info('NUM loaded: ' + s['NUM'])
	return ID, NUM

# Function to write settings to a json file
def write_settings(ID,NUM):
	logging.info("Saving settings: ID - %s, NUM - %s" %(ID,NUM))
	# Initialize data structre to be saved to file
	data = {}
	data['settings'] = []
	data['settings'].append({
		'ID': str(ID),
		'NUM': str(NUM)
	})
	# Open file amd save data
	with open('settings_.json', 'w') as outfile:
		json.dump(data, outfile,indent=4)

"""
##----------Hardware Commands----------##
"""
def LED_light(secconds, count):
	logging.info("LED light :)")
	i = 0
	while i < count:
		GPIO.output(LED, GPIO.HIGH)
		time.sleep(secconds/2)
		GPIO.output(LED, GPIO.LOW)
		time.sleep(secconds/2)
		i +=1

def check_float(false_detect_time = 2):
	# Check if the float swich is high for the false_detect_time
	temp_time = time.perf_counter()
	while GPIO.input(FLOAT) == 0:
		if time.perf_counter() - temp_time > false_detect_time:
			logging.info("The float was activated for %s seconds" % false_detect_time)
			# LED_light(0.5,4)
			print("Float active")
			return "Yes"
		time.sleep(0.5)
	print("Float not active")
	return "No"

def check_voltage(ina260):
	voltage = ina260.get_bus_voltage()
	current = ina260.get_current()

	print('V=%6.4f,I=%6.4f,' % (voltage,current))
	logging.debug('V=%6.4f,I=%6.4f,' % (voltage,current))

	return voltage, current

"""
##----------Modem Commands----------##
"""
# Initialise the modem
def modem_init():
    modem = smsModem()
    modem.connect()
    modem.config()
    # modem.clearMessage("ALL")
    # time.sleep(1)
    modem.signalTest()
    return modem

# Put the modem to sleep
def modem_sleep(modem):
    modem.disconnect()
    print("entering Sleep")
    GPIO.output(DTR, GPIO.HIGH)

"""
##--------------------Start of Executing code--------------------##
"""
# Setup GPIO Pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(FLOAT, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Float Switch pin
GPIO.setup(DTR, GPIO.OUT, initial=GPIO.LOW) # DTR pin on 4g module
GPIO.setup(W_DISABLE, GPIO.OUT, initial=GPIO.LOW) # W_DISABLE pin on 4g module
GPIO.setup(RI, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # RI pin on 4g module
GPIO.setup(PERST, GPIO.OUT, initial=GPIO.LOW) # PERST pin on 4g module
GPIO.setup(LED, GPIO.OUT, initial=GPIO.LOW) # LED pin
# GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Button pin

# Initilise INA260 module
ina260 = INA260(dev_address=0x40)
ina260.reset_chip()
time.sleep(0.1)

# Initilise ds3231 module
ds3231 = SDL_DS3231.SDL_DS3231(1, 0x68)

# Update the pi time to match RTC
update_pi_time()

# Setup Logging
try:
    logging.basicConfig(
        filename='logs/testing.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
        )
except:
    print("Log file could not be made")

# Load settings from settings_.json
ID, NUM = load_settings()

# Check Battery Voltage
voltage,current = check_voltage(ina260)

if check_float() == "Yes":
    logging.info('Float switch is active')
    # set gpio to high here to turn on modem

    # init the modem
    modem = modem_init()
    # Send a text message
    modem.sendMessage(
        emulation=parsed_args.emulation,recipient=NUM.encode(),
        message=b'Module %s Has Detected Water! Voltage=%4.2fV' % (ID.encode(),voltage)
        )
    modem.disconnect()
    # set gpio to low here to turn off modem

if (11.5 > voltage):
    logging.warning("Voltage VERY LOW: %sV" % voltage)
    print("send text for VERY LOW")
    # check if modem has been initialised
    try:
        print("Is Modem Initialised?")
        modem.connect()
        print("Modem Initialised")
    except:
        print("Initialise Modem")
        modem = modem_init()

    # Send a text message
    modem.sendMessage(
        emulation=parsed_args.emulation,recipient=NUM.encode(),
        message=b'Module %s VERY LOW VOLTAGE WARNING!! Voltage=%4.2f Module may run out of power, consider recharging the battery' % (ID.encode(),voltage)
        )
else:
    logging.warning("Voltage UNKNOWN: %sV" % voltage)
    print("unknown voltage")

while(True):
    print("start")
    set_timer(0,0,3)
    print("wait 3s")
    time.sleep(3)
    print("wait another 1s")
    time.sleep(1)
