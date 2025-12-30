import RPi.GPIO as GPIO
import time
from RPLCD.i2c import CharLCD
import threading
import subprocess
import numpy as np
import cv2

# ==========================
#  CAMERA THREAD
# ==========================
def camera_stream():
    command = [
    "rpicam-vid",
    "--width", "640",
    "--height", "480",
    "--framerate", "30",
    "--codec", "yuv420",
    "--inline",
    "--nopreview",   # <---- THIS PREVENTS SECOND CAMERA WINDOW
    "-t", "0",
    "-o", "-"
]
    print("🎥 Starting rpicam-vid stream...")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    width, height = 640, 480
    frame_size = width * height * 3 // 2

    while camera_running:
        raw = process.stdout.read(frame_size)
        if len(raw) != frame_size:
            print("⚠️ Camera failed to read frame.")
            break

        yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(height * 1.5), width))
        frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

        cv2.imshow("Vehicle Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("📷 Stopping camera...")
    process.terminate()
    cv2.destroyAllWindows()

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

zero_offset = zero_offset // valid if valid > 0 else 0
print("Zero offset:", zero_offset)

lcd.clear()
lcd.write_string("Ready...")

time.sleep(1)

# ==========================
# START CAMERA THREAD
# ==========================
camera_running = True
thread = threading.Thread(target=camera_stream, daemon=False)
thread.start()

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
        weight = abs(raw / 106.0)

        # FILTER SPIKES
        if weight > 5000:
            continue

        # DECISION
        if metal_detected:
            status = "Metal Detected"
        elif weight > 150:
            status = "Vehicle Overweight"
        else:
            status = "Safe Vehicle"

        print(f"Metal: {metal_detected}, Weight: {round(weight,2)} g -> {status}")

        lcd.clear()
        lcd.write_string(status)

        time.sleep(0.7)

except KeyboardInterrupt:
    print("Stopping System...")

finally:
    camera_running = False
    time.sleep(1)
    lcd.clear()
    lcd.write_string("Stopped")
    GPIO.cleanup()
    print("Program stopped.")
