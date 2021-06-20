from RTC_SDL_DS3231 import SDL_DS3231
import smbus
import time
import os
import logging

ds3231 = SDL_DS3231.SDL_DS3231(1, 0x68)

SECONDS_REG = 0x00
ALARM1_SECONDS_REG = 0x07

CONTROL_REG = 0x0E
STATUS_REG = 0x0F

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
    # set the alarm
    write_time_to_clock(ALARM1_SECONDS_REG, clock_time[4]+hours, clock_time[5]+minutes, clock_time[6]+seconds)
    # set the alarm to match hours minutes and seconds from clock time
    # need to set some flags
    set_alarm1_mask_bits((True, False, False, False))
    enable_alarm1()
    clear_alarm1_flag()


print("Raspberry Pi=\t" + time.strftime("%Y-%m-%d %H:%M:%S"))
print("Ds3231=\t\t%s" % ds3231.read_datetime())
# ds3231.write_now()
# print("Ds3231=\t\t%s" % ds3231.read_datetime())
os.system('date')
os.system('sudo date -s "%s"' % ds3231.read_datetime())
os.system('date')

while(True):
    print("start")
    set_timer(0,0,5)
    print("wait 5s")
    time.sleep(5)
    print("wait another 5s")
    time.sleep(5)