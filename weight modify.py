import RPi.GPIO as GPIO
import time

DT = 6
SCK = 5

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SCK, GPIO.OUT)

def readCount():
    Count = 0

    GPIO.setup(DT, GPIO.OUT)
    GPIO.output(DT, 1)
    GPIO.output(SCK, 0)
    GPIO.setup(DT, GPIO.IN)

    timeout = time.time() + 1
    while GPIO.input(DT) == 1:
        if time.time() > timeout:
            return None

    for i in range(24):
        GPIO.output(SCK, 1)
        Count = Count << 1
        GPIO.output(SCK, 0)
        if GPIO.input(DT) == 0:
            Count += 1

    GPIO.output(SCK, 1)
    Count = Count ^ 0x800000
    GPIO.output(SCK, 0)

    return Count


print("Getting base sample (remove all weight)...")
sample = None
while sample is None:
    sample = readCount()
print("Base:", sample)

# Zeroing / tare value calculation
print("Calibrating zero offset...")
time.sleep(1)

zero_offset = 0
count = 0
valid = 0

# Take 20 samples for automatic zero drift correction
for i in range(20):
    val = readCount()
    if val is not None:
        zero_offset += (val - sample)
        valid += 1
    time.sleep(0.05)

if valid > 0:
    zero_offset = zero_offset // valid
else:
    zero_offset = 0

print("Zero offset:", zero_offset)
print("Weight measurement ready...\n")


try:
    while True:
        count = readCount()
        if count is None:
            print("Sensor not ready")
            continue

        # Apply zero correction
        raw = (count - sample) - zero_offset

        # Weight calculation
        weight = abs(raw / 106.0)

        # Ignore impossible spikes
        if weight > 5000:
            continue

        print("Weight:", round(weight, 2), "g")
        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Stopped.")
