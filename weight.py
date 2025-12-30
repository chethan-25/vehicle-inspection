import RPi.GPIO as GPIO
import time

DT = 6
SCK = 5

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SCK, GPIO.OUT)

def readCount():
    Count = 0

    # Prepare DT line
    GPIO.setup(DT, GPIO.OUT)
    GPIO.output(DT, 1)
    GPIO.output(SCK, 0)
    GPIO.setup(DT, GPIO.IN)

    # Wait for DT to go LOW (ready)
    timeout = time.time() + 1  # 1 sec timeout
    while GPIO.input(DT) == 1:
        if time.time() > timeout:
            return None  # Sensor not responding

    # Read 24 bits
    for i in range(24):
        GPIO.output(SCK, 1)
        Count = Count << 1
        GPIO.output(SCK, 0)
        if GPIO.input(DT) == 0:
            Count += 1

    # Set gain 128
    GPIO.output(SCK, 1)
    Count = Count ^ 0x800000   # Convert signed value
    GPIO.output(SCK, 0)

    return Count

# Calibration
print("Getting base sample...")
sample = None
while sample is None:
    sample = readCount()
print("Base:", sample)

# Main loop
try:
    while True:
        count = readCount()
        if count is None:
            print("Sensor not ready")
            continue

        weight = abs((count - sample) / 106.0)
        print("Weight:", weight, "g")
        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Stopped.")

