from hcsr04 import HCSR04
from time import sleep


def get_dist():
  sensor = HCSR04(trigger_pin=4, echo_pin=16, echo_timeout_us=10000)
  return sensor.distance_cm()