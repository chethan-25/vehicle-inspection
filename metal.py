# # import RPi.GPIO as GPIO
# # import time
# # 
# # METAL_PIN = 17
# # 
# # GPIO.setmode(GPIO.BCM)
# # GPIO.setup(METAL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Add pull-up
# # 
# # try:
# #     while True:
# #         state = GPIO.input(METAL_PIN)
# #         print("GPIO State:", state)
# # 
# #         if state == GPIO.LOW:
# #             print("🔔 Metal Detected!")
# #         else:
# #             print("⏳ No Metal")
# # 
# #         time.sleep(1)
# # 
# # except KeyboardInterrupt:
# #     GPIO.cleanup()
# import RPi.GPIO as GPIO
# import time
# 
# # Use BCM numbering
# GPIO.setmode(GPIO.BCM)
# 
# # Metal sensor output pin
# METAL_PIN = 17  # GPIO 17, Pin 11 on Raspberry Pi
# 
# # Setup pin as input
# GPIO.setup(METAL_PIN, GPIO.IN)
# 
# print("Metal Detector Test (CTRL+C to exit)")
# 
# try:
#     while True:
#         if GPIO.input(METAL_PIN):
#             print("Metal Detected! 🔔")
#         else:
#             print("No Metal")
#         time.sleep(1)  # Check every 200ms
# except KeyboardInterrupt:
#     print("\nProgram stopped")
#     GPIO.cleanup()
# print("Stopped.")

import RPi.GPIO as GPIO
import time
from RPLCD.i2c import CharLCD

# === Setup LCD ===
lcd = CharLCD('PCF8574', 0x27)  # Change 0x27 to your LCD I2C address
lcd.clear()
lcd.write_string("Metal Detector")

# === Setup GPIO ===
METAL_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(METAL_PIN, GPIO.IN)

print("Metal Detector Test (CTRL+C to exit)")

try:
    while True:
        if GPIO.input(METAL_PIN):
            msg = "Metal Detected! 🔔"
        else:
            msg = "No Metal"

        # Print to terminal
        print(msg)

        # Display on LCD
        lcd.clear()
        lcd.write_string(msg)

        time.sleep(1)

except KeyboardInterrupt:
    print("\nProgram stopped")
    lcd.clear()
    lcd.write_string("Stopped.")
    GPIO.cleanup()
