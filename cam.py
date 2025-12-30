import cv2
import subprocess
import numpy as np

# Command to start the rpicam video stream
# -t 0 = run indefinitely
# --inline ensures frames can be streamed
command = [
    "rpicam-vid",
    "--width", "640",
    "--height", "480",
    "--framerate", "30",
    "--codec", "yuv420",
    "--inline",
    "-t", "0",
    "-o", "-"  # output to stdout
]

print("?? Starting rpicam-vid stream...")

# Start rpicam-vid as a subprocess
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

width, height = 640, 480
frame_size = width * height * 3 // 2  # YUV420p frame size

print("? Stream started. Press 'q' to quit.")

while True:
    # Read raw frame data from stdout
    raw = process.stdout.read(frame_size)
    if len(raw) != frame_size:
        print("?? No frame received, exiting...")
        break

    # Convert YUV to BGR for OpenCV
    yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(height * 1.5), width))
    frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

    cv2.imshow("Live Stream - Press Q to Quit", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

process.terminate()
cv2.destroyAllWindows()
