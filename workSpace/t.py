from ir_tx.nec import NEC
from ir_tx.sony import SONY_12, SONY_15, SONY_20
from ir_tx.philips import RC5, RC6_M0
from machine import Pin
import time

led = Pin(22, Pin.OUT)
irb = NEC(led, 38000)
options = [0x46, 0x47, 0x40, 0x43, 0x15, 0x09]
index = 0
while True:
    irb.transmit(0x0, options[0], True)
    index += 1
    if index == len(options) - 1:
        index = 0
    time.sleep(.5)