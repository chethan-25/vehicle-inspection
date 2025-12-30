import time
from hx711 import HX711
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
hx = HX711(6,5)

while True:
    print(hx.get_raw_data())
    time.sleep(0.3)
