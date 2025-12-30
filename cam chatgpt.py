from picamera2 import Picamera2
import cv2
import time
from PIL import Image
import pytesseract

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

time.sleep(1)

while True:
    frame = picam2.capture_array()
    cv2.imshow("Image", frame)
    
    key = cv2.waitKey(1)
    if key == 27:   # ESC to capture and exit
        break

# Save captured frame
cv2.imwrite("2.png", frame)
print("Image saved as 2.png")

picam2.stop()
cv2.destroyAllWindows()

# OCR
img = Image.open("2.png")
text = pytesseract.image_to_string(img)
print("\nExtracted Text:\n", text)
