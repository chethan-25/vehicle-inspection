import time
import RPi.GPIO as GPIO
from hx711 import HX711
import statistics

DT_PIN = 6
SCK_PIN = 5

GPIO.setmode(GPIO.BCM)

hx = HX711(DT_PIN, SCK_PIN)

def get_filtered_value():
    data = hx.get_raw_data()     # returns a list
    # Remove extreme outliers
    data = [x for x in data if 1000 < x < 2000000]
    # If list empty, return 0
    if len(data) == 0:
        return 0
    # Return the median (best stable value)
    return int(statistics.median(data))

print("Reading filtered raw values...")

try:
    while True:
        raw = get_filtered_value()
        print("Raw:", raw)
        time.sleep(0.3)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Stopped")
