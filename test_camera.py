import cv2
import numpy as np 
import argparse
import time

#cap = cv2.VideoCapture(1)
cap = cv2.VideoCapture(0)  # Open camera

while True:
		_, frame = cap.read()
		cv2.imshow("Image", frame)
		cv2.imshow("Image1", frame)
		
		key = cv2.waitKey(1)
		if key == 27:
			break
cap.release()
cv2.imwrite('2.png',frame)
import pytesseract
from PIL import Image
img =Image.open ('2.png')
text = pytesseract.image_to_string(img, config='')
print (text)
