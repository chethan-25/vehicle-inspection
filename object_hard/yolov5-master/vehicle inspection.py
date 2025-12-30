# ==========================
# VEHICLE INSPECTION SYSTEM (Raspberry Pi)
# ==========================
import pathlib
pathlib.WindowsPath = pathlib.PosixPath
import time
import threading
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import numpy as np
import cv2
from picamera2 import Picamera2
import torch

# ==========================
#  YOLOv5 MODEL SETUP
# ==========================
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, force_reload=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model.to(device)

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
lcd.clear()
lcd.write_string("Calibrating...")
sample = None
while sample is None:
    sample = readCount()

zero_offset = 0
valid = 0
for i in range(20):
    v = readCount()
    if v is not None:
        zero_offset += (v - sample)
        valid += 1
    time.sleep(0.05)
zero_offset = zero_offset // valid if valid > 0 else 0
lcd.clear()
lcd.write_string("Ready...")

# ==========================
#  GLOBAL VARIABLES
# ==========================
camera_running = True
sensor_running = True
frame_output = None
vehicle_status = "Safe Vehicle"
person_count = 0
weapon_detected = False
current_weight = 0
metal_detected_flag = False

# ==========================
#  CAMERA THREAD (Picamera2 + OpenCV)
# ==========================
def camera_thread():
    global frame_output, person_count, weapon_detected

    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
    picam2.start()

    while camera_running:
        frame = picam2.capture_array()

        # YOLOv5 detection (force numpy for easy processing)
        results = model(frame)
        dets = results.xyxy[0].cpu().numpy()

        person_count_local = 0
        weapon_detected_local = False

        for det in dets:
            x1, y1, x2, y2, conf, cls = det
            conf = float(conf)
            cls = int(cls)
            label = results.names[cls].lower()

            if conf < 0.3:  # filter low confidence
                continue

            color = (0, 255, 0) if label == "person" else (0, 0, 255)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if label == "person":
                person_count_local += 1
            if label in ["knife", "gun", "weapon"]:
                weapon_detected_local = True

        # Update global values
        frame_output = frame
        person_count = person_count_local
        weapon_detected = weapon_detected_local

        cv2.imshow("Vehicle Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.close()
    cv2.destroyAllWindows()
    print("Camera stopped.")

# ==========================
#  SENSOR THREAD
# ==========================
def sensor_thread():
    global current_weight, metal_detected_flag, vehicle_status

    while sensor_running:
        metal_detected_flag = GPIO.input(METAL_PIN)
        count = readCount()
        if count is None:
            continue

        raw = (count - sample) - zero_offset
        current_weight = abs(raw / 106.0)

        if current_weight > 5000:
            continue

        # Decision logic
        if weapon_detected:
            vehicle_status = "Weapon Detected"
        elif person_count > 3:
            vehicle_status = "Over Persons"
        elif metal_detected_flag:
            vehicle_status = "Metal Detected"
        elif current_weight > 150:
            vehicle_status = "Vehicle Overweight"
        else:
            vehicle_status = "Safe Vehicle"

        lcd.clear()
        lcd.write_string(vehicle_status)
        time.sleep(0.3)

# ==========================
#  MAIN
# ==========================
try:
    threading.Thread(target=camera_thread, daemon=True).start()
    threading.Thread(target=sensor_thread, daemon=True).start()

    print("Press 'q' in camera window to stop.")
    while True:
        time.sleep(0.5)
        print(f"Persons: {person_count} | Weapon: {weapon_detected} | Weight: {current_weight:.1f} | Metal: {metal_detected_flag} | Status: {vehicle_status}")

except KeyboardInterrupt:
    print("Stopping system...")

finally:
    camera_running = False
    sensor_running = False
    time.sleep(1)
    GPIO.cleanup()
    lcd.clear()
    print("System stopped.")
