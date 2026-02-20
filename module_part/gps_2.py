import cv2
import threading
from ultralytics import YOLO
import serial
from datetime import datetime
import os
import json
import time

model = YOLO('train4/weights/best.pt')

output_dir = "detections"
os.makedirs(output_dir, exist_ok=True)

json_file = os.path.join(output_dir, "gps_log.json")

json_data = []
if os.path.exists(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                json_data = json.loads(content)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        json_data = []


def save_json():
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)


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
        ser = serial.Serial('/dev/ttyAMA10', baudrate=9600, timeout=1)
        while True:
            line = ser.readline().decode('ascii', errors='replace').strip()
            if not line:
                continue
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

                        detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        detection_details = []
                        for box in res[0].boxes:
                            cls_id = int(box.cls[0].item())
                            conf = float(box.conf[0].item())
                            cls_name = model.names[cls_id]
                            detection_details.append(f"{cls_name} ({conf:.2f})")

                        description_text = f"Время: {detection_time} | Объекты: {', '.join(detection_details)}"

                        filename = f"detection_{frame_count}_{detection_time}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, annotated_frame)

                        entry = {
                            "coordinates": [lat, lon],
                            "image": filename,
                            "title": "...",
                            "description": description_text
                        }
                        json_data.append(entry)
                        save_json()
                    else:
                        print("GPS недоступен, запись в формате JSON пропущена.")

        cv2.imshow("USB YOLO", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    save_json()
    stream.stop()
    cv2.destroyAllWindows()
