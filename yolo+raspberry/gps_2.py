import cv2
import threading
from ultralytics import YOLO
import serial
from datetime import datetime
import os
import csv
import time

model = YOLO('train4/weights/best.pt')

output_dir = "detections"
os.makedirs(output_dir, exist_ok=True)

csv_file = os.path.join(output_dir, "gps_log.csv")
if not os.path.exists(csv_file):
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # "timestamp", "frame_id", "filename", "lat", "lat_dir", "lon", "lon_dir"
        writer.writerow(["timestamp", "frame_id", "filename", "lat", "lon"])

class USBVideoStream:
    def __init__(self, src=0, width=640, height=480):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.ret, self.frame = self.cap.read()
        self.stopped = False
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

last_gps = None
lock = threading.Lock()

def read_gps():
    global last_gps
    try:
        ser = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)
        while True:
            line = ser.readline().decode('ascii', errors='replace').strip()
            if not line:
                continue
            print("GPS raw:", line)
            parts = line.split(',')
            if parts[0] in ("$GPGGA", "$GNGGA") and len(parts) >= 6:
                with lock:
                    last_gps = (parts[2], parts[3], parts[4], parts[5])
    except Exception as e:
        print(f"GPS error: {e}")

threading.Thread(target=read_gps, daemon=True).start()

def process_frame(frame):
    res = model(frame, conf=0.5)
    annotated = res[0].plot()
    return annotated, res

stream = USBVideoStream(src=0, width=640, height=480)
frame_count = 0

try:
    while True:
        frame = stream.read()
        if frame is None:
            continue

        frame_count += 1

        if frame_count % 2 != 0:
            annotated_frame = frame
        else:
            annotated_frame, res = process_frame(frame)

            if len(res[0].boxes) > 0:
                wait_time = 0
                while last_gps is None and wait_time < 5:
                    print("Waiting for GPS...")
                    time.sleep(0.5)
                    wait_time += 0.5

                with lock:
                    if last_gps:
                        lat, lat_dir, lon, lon_dir = last_gps
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        filename = f"detection_{frame_count}_{timestamp}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, annotated_frame)
                        with open(csv_file, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([timestamp, frame_count, filename, lat, lon])
                    else:
                        print("GPS недоступен, запись в формате CSV пропущена.")

        cv2.imshow("USB YOLO", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    stream.stop()
    cv2.destroyAllWindows()