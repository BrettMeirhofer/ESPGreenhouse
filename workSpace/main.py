# This example demonstrates a simple temperature sensor peripheral.
# The sensor's local value updates every second, and it will notify
# any connected central every 10 seconds.

import bluetooth
import struct
import time
from ble_advertising import advertising_payload
from machine import Pin
from machine import Timer
from sonar import get_dist

from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_GATTC_READ_DONE = const(16)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
SONAR_ATTR = (
    bluetooth.UUID(0x2A6E),
    _FLAG_READ | _FLAG_WRITE,
)

TOGGLE_ATTR_1 = (
    bluetooth.UUID(0x2A6F),
    _FLAG_READ | _FLAG_WRITE,
)

TOGGLE_ATTR_2 = (
    bluetooth.UUID(0x2A61),
    _FLAG_READ | _FLAG_WRITE,
)

TOGGLE_ATTR_3 = (
    bluetooth.UUID(0x2A62),
    _FLAG_READ | _FLAG_WRITE,
)

TOGGLE_ATTR_4 = (
    bluetooth.UUID(0x2A63),
    _FLAG_READ | _FLAG_WRITE,
)

_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (SONAR_ATTR, TOGGLE_ATTR_1, TOGGLE_ATTR_2, TOGGLE_ATTR_3, TOGGLE_ATTR_4,),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)


class BLETemperature:
    def __init__(self):
        ble = bluetooth.BLE()
        self.led = Pin(2, Pin.OUT)
        self.timer1 = Timer(0)
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        (self.handles,) = self._ble.gatts_register_services((_ENV_SENSE_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(
            name="ESP32", services=[_ENV_SENSE_UUID], appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER
        )
        self._advertise()
        self.timer1.init(period=100, mode=Timer.PERIODIC, callback=lambda t: self.led.value(not self.led.value()))

        relay_pins = [17, 5, 18, 19]
        self.relays = []
        for pins in relay_pins:
            relay = Pin(pins, Pin.OUT)
            relay.value(1)
            self.relays.append(relay)

        self.relay_handles = (self.handles[1], self.handles[2], self.handles[3], self.handles[4])
        for x in self.relay_handles:
            self._ble.gatts_write(x, "1".encode("UTF-8"))

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self.led.value(1)
            self.timer1.deinit()

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
            self.timer1.init(period=100, mode=Timer.PERIODIC, callback=lambda t: self.led.value(not self.led.value()))

        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            self.update_state(conn_handle, attr_handle)

    def update_state(self, conn_handle, attr_handle):
        if attr_handle in self.relay_handles:
            index = self.relay_handles.index(attr_handle)
            request_state = self._ble.gatts_read(self.handles[index + 1])
            if request_state == b'':
                state = not self.relays[index].value()
            else:
                state = int(request_state)

            self.relays[index].value(state)
            self._ble.gatts_write(self.handles[index + 1], str(state).encode("UTF-8"))

        elif attr_handle == self.handles[0]:
            self.set_dist()

    def set_dist(self):
        # Data is sint16 in degrees Celsius with a resolution of 0.01 degrees Celsius.
        # Write the local value, ready for a central to read.
        self._ble.gatts_write(self.handles[0], str(round(get_dist())).encode("UTF-8"))

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)


def demo():
    temp = BLETemperature()


if __name__ == "__main__":
    demo()
