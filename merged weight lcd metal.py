import RPi.GPIO as GPIO
import time
from RPLCD.i2c import CharLCD

# ==========================
#  LCD SETUP
# ==========================
lcd = CharLCD('PCF8574', 0x27)
lcd.clear()
lcd.write_string("Security System")
time.sleep(1)

# ==========================
#  METAL SENSOR SETUP
# ==========================
METAL_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(METAL_PIN, GPIO.IN)

# ==========================
#  LOAD CELL SETUP (HX711)
# ==========================
DT = 6
SCK = 5

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


# ==========================
#  CALIBRATION
# ==========================

print("Remove all weight... capturing base sample...")
sample = None
while sample is None:
    sample = readCount()

print("Base sample:", sample)

# Zeroing correction
print("Calibrating zero offset...")
time.sleep(1)

zero_offset = 0
valid = 0

for i in range(20):
    v = readCount()
    if v is not None:
        zero_offset += (v - sample)
        valid += 1
    time.sleep(0.05)

if valid > 0:
    zero_offset //= valid
else:
    zero_offset = 0

print("Zero offset:", zero_offset)
lcd.clear()
lcd.write_string("Ready...")
time.sleep(1)

# ==========================
# MAIN LOOP
# ==========================
print("System Started (CTRL+C to stop)")

try:
    while True:
        # Read Metal Sensor
        metal_detected = GPIO.input(METAL_PIN)

        # Read Load Cell
        count = readCount()
        if count is None:
            continue

        raw = (count - sample) - zero_offset
        weight = abs(raw / 106.0)  # in grams

        # FILTER SPIKES
        if weight > 5000:
            continue

        # DECISION LOGIC
        if metal_detected:
            status = "Metal Detected"
        elif weight > 150:
            status = "Weapon Detected"
        else:
            status = "Safe"

        # Print to Terminal
        print(f"Metal: {metal_detected}, Weight: {round(weight,2)} g ? {status}")

        # LCD Display
        lcd.clear()
        lcd.write_string(status)

        time.sleep(0.7)

except KeyboardInterrupt:
    lcd.clear()
    lcd.write_string("Stopped")
    GPIO.cleanup()
    print("Program stopped.")
