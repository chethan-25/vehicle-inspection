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
print("Loading YOLO models...")

# COCO PERSON model
model_person = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Custom weapon model
model_weapon = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt')

# Set thresholds
model_person.conf = 0.50
model_weapon.conf = 0.35
model_weapon.iou = 0.45

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model_person.to(device)
model_weapon.to(device)

print("Models loaded successfully!")

# ==========================
#  LCD SETUP
# ==========================
lcd = CharLCD('PCF8574', 0x27)
lcd.clear()
lcd.write_string("Security System")
time.sleep(1)

# ==========================
# GPIO SETUP
# ==========================
GPIO.setmode(GPIO.BCM)

# MQ-2 GAS SENSOR (DO pin)
GAS_PIN = 22
GPIO.setup(GAS_PIN, GPIO.IN)

# METAL SENSOR
METAL_PIN = 23
GPIO.setup(METAL_PIN, GPIO.IN)

# LOAD CELL (HX711)
DT = 6
SCK = 5
GPIO.setup(SCK, GPIO.OUT)


# ==========================
#  READ HX711
# ==========================
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
# GLOBAL VARIABLES
# ==========================
camera_running = True
sensor_running = True

person_count = 0
weapon_detected = False
metal_detected_flag = False
gas_detected_flag = False
current_weight = 0

vehicle_status = "Safe Vehicle"


# ==========================
# CAMERA THREAD
# ==========================
def camera_thread():
    global frame_output, person_count, weapon_detected

    picam2 = Picamera2()
    picam2.configure(
        picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
    )
    picam2.start()

    while camera_running:
        frame = picam2.capture_array()

        # YOLO inference
        results_person = model_person(frame)
        results_weapon = model_weapon(frame)

        det_person = results_person.xyxy[0].cpu().numpy()
        det_weapon = results_weapon.xyxy[0].cpu().numpy()

        person_count_local = 0
        weapon_detected_local = False

        # PERSON detection
        for det in det_person:
            x1, y1, x2, y2, conf, cls = det
            if int(cls) == 0:
                person_count_local += 1
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame, "person", (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # WEAPON detection
        for det in det_weapon:
            x1, y1, x2, y2, conf, cls = det
            label = model_weapon.names[int(cls)]

            if label in ["gun", "knife", "hammer"]:
                weapon_detected_local = True
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                cv2.putText(frame, label, (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        person_count = person_count_local
        weapon_detected = weapon_detected_local

        cv2.imshow("Vehicle Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.close()
    cv2.destroyAllWindows()
    print("Camera stopped.")


# ==========================
# SENSOR THREAD
# ==========================
def sensor_thread():
    global current_weight, metal_detected_flag, gas_detected_flag, vehicle_status

    while sensor_running:

        # -------------------------------
        # GAS SENSOR LOGIC (YOUR REQUEST)
        # -------------------------------
        gas_raw = GPIO.input(GAS_PIN)  # HIGH = no gas, LOW = gas detected

        if gas_raw == 0:
            gas_detected_flag = True         # GAS PRESENT
        else:
            gas_detected_flag = False        # NO GAS

        # METAL SENSOR
        metal_detected_flag = GPIO.input(METAL_PIN)

        # LOAD CELL
        count = readCount()
        if count is not None:
            raw = (count - sample) - zero_offset
            current_weight = abs(raw / 106.0)

        # -------------------------------
        # DECISION MAKING
        # -------------------------------
        if gas_detected_flag:
            vehicle_status = "Gas Detected"
        elif weapon_detected:
            vehicle_status = "Weapon Detected"
        elif person_count > 1:
            vehicle_status = "Over Person"
        elif metal_detected_flag:
            vehicle_status = "Metal Found"
        elif current_weight > 150:
            vehicle_status = "Extra Load"
        else:
            vehicle_status = "Safe Vehicle"

        lcd.clear()
        lcd.write_string(vehicle_status)
        time.sleep(0.3)
# ==========================
# MAIN LOOP
# ==========================
try:
    threading.Thread(target=camera_thread, daemon=True).start()
    threading.Thread(target=sensor_thread, daemon=True).start()

    print("Press 'q' in camera window to stop.")

    while True:
        time.sleep(0.5)
        print(f"Persons: {person_count} | Weapon: {weapon_detected} | Gas: {gas_detected_flag} | "
              f"Metal: {metal_detected_flag} | Weight: {current_weight:.1f} | Status: {vehicle_status}")

except KeyboardInterrupt:
    print("Stopping system...")

finally:
    camera_running = False
    sensor_running = False
    time.sleep(1)
    GPIO.cleanup()
    lcd.clear()
    print("System stopped.")