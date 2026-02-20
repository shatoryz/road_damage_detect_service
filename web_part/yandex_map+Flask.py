from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import sqlite3
import json
import torch
from ultralytics import YOLO

app = Flask(__name__)

UPLOAD_FOLDER_IMAGES = 'uploads/images'
UPLOAD_FOLDER_DETECTED = 'uploads/detected'
DATA_FOLDER = 'data'
MARKERS_FILE = os.path.join(DATA_FOLDER, 'markers.json')

os.makedirs(UPLOAD_FOLDER_IMAGES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_DETECTED, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

if not os.path.exists(MARKERS_FILE):
    with open(MARKERS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

print("Загрузка модели YOLOv8...")
try:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Устройство: {device.upper()}")
    model = YOLO(r'C:\Users\shatory\PyCharmMiscProject\yolo+raspberry\popitka3\runs\detect\train\weights\best.pt')
    model.to(device)
    print("Модель YOLO загружена!")
except Exception as e:
    print(f"Ошибка загрузки YOLO: {e}")
    model = None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_objects(image_path, min_confidence=0.3):
    if model is None:
        return [], None
    try:
        results = model(image_path, conf=min_confidence, verbose=False, imgsz=640)
        result = results[0]
        boxes = result.boxes
        found_objects = []
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = result.names[cls]
            found_objects.append({
                'class': label,
                'confidence': round(conf, 2),
                'class_id': cls
            })

        detection_path = None
        if found_objects:
            det_filename = f"det_{os.path.basename(image_path)}"
            detection_path = os.path.join(UPLOAD_FOLDER_DETECTED, det_filename)
            result.save(detection_path)
        return found_objects, detection_path
    except Exception as e:
        print(f"Ошибка детекции {image_path}: {e}")
        return [], None


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT NOT NULL, 
        email TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS markers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coordinates TEXT NOT NULL,
        image TEXT,
        title TEXT,
        description TEXT,
        detected_objects TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not name or not email or not password or not confirm_password:
            return "Please fill all fields!"
        if password != confirm_password:
            return "Passwords do not match!"
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "User with this email already exists!"
        finally:
            conn.close()
        return redirect(url_for('map_page'))
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            return redirect(url_for('map_page'))
        else:
            error = "Invalid email or password"
    return render_template('login.html', error=error)


@app.route('/map')
def map_page():
    return render_template('yandex_api.html')


@app.route('/upload_images', methods=['POST'])
def upload_images():
    if 'fileToUpload' not in request.files:
        return jsonify({'error': 'Файл не выбран!'}), 400

    files = request.files.getlist('fileToUpload')
    uploaded_files = []
    rejected_files = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            filename = original_filename
            name, ext = os.path.splitext(original_filename)
            counter = 1
            img_path = os.path.join(UPLOAD_FOLDER_IMAGES, filename)
            while os.path.exists(img_path):
                filename = f"{name}_{counter}{ext}"
                img_path = os.path.join(UPLOAD_FOLDER_IMAGES, filename)
                counter += 1
            file.save(img_path)
            print(f"Сохранено изображение: {filename}")
            detected_objects, detection_path = detect_objects(img_path, min_confidence=0.3)
            if detected_objects:
                uploaded_files.append({
                    'original_name': original_filename,
                    'saved_name': filename,
                    'url': f'/uploads/images/{filename}',
                    'detection_url': f'/uploads/detected/det_{filename}' if detection_path else None,
                    'detected_objects': detected_objects,
                    'objects_count': len(detected_objects)
                })
                print(f"Найдено объектов: {len(detected_objects)}")
            else:
                uploaded_files.append({
                    'original_name': original_filename,
                    'saved_name': filename,
                    'url': f'/uploads/images/{filename}',
                    'detection_url': None,
                    'detected_objects': [],
                    'objects_count': 0
                })
                rejected_files.append({
                    'original_name': original_filename,
                    'reason': 'YOLO не обнаружила объектов (файл сохранен)'
                })

    return jsonify({
        'success': True,
        'uploaded': len(uploaded_files),
        'rejected': len(rejected_files),
        'files': uploaded_files,
        'rejected_files': rejected_files
    })


@app.route('/get_images', methods=['GET'])
def get_images():
    images = []
    if os.path.exists(UPLOAD_FOLDER_IMAGES):
        for filename in os.listdir(UPLOAD_FOLDER_IMAGES):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                det_filename = f"det_{filename}"
                det_path = os.path.join(UPLOAD_FOLDER_DETECTED, det_filename)
                has_detection = os.path.exists(det_path)
                images.append({
                    'name': filename,
                    'url': f'/uploads/images/{filename}',
                    'has_detection': has_detection,
                    'detection_url': f'/uploads/detected/{det_filename}' if has_detection else None
                })
    return jsonify(images)


@app.route('/save_markers', methods=['POST'])
def save_markers():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Неверный формат данных'}), 400

    valid_markers = []
    for marker in data:
        image_name = marker.get('image', '')
        img_path = os.path.join(UPLOAD_FOLDER_IMAGES, image_name)

        if os.path.exists(img_path):
            valid_markers.append(marker)
            print(f"Метка принята: image='{image_name}'")
        else:
            if image_name:
                base = os.path.splitext(image_name)[0]
                similar = [f for f in os.listdir(UPLOAD_FOLDER_IMAGES) if f.startswith(base)]
                print(f"Метка отклонена: '{image_name}' не найден. Похожие: {similar}")
            else:
                print(f"Метка отклонена: пустое имя изображения")

    with open(MARKERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(valid_markers, f, ensure_ascii=False, indent=2)

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM markers')
    for marker in valid_markers:
        cursor.execute(
            'INSERT INTO markers (coordinates, image, title, description, detected_objects) VALUES (?, ?, ?, ?, ?)',
            (
                json.dumps(marker.get('coordinates', [])),
                marker.get('image', ''),
                marker.get('title', ''),
                marker.get('description', ''),
                json.dumps(marker.get('detected_objects', []))
            )
        )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Сохранено {len(valid_markers)} меток',
        'saved': len(valid_markers),
        'rejected': len(data) - len(valid_markers)
    })


@app.route('/get_markers', methods=['GET'])
def get_markers():
    if os.path.exists(MARKERS_FILE):
        with open(MARKERS_FILE, 'r', encoding='utf-8') as f:
            markers = json.load(f)
        return jsonify(markers)
    return jsonify([])


@app.route('/clear_markers', methods=['POST'])
def clear_markers():
    with open(MARKERS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM markers')
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Все метки удалены'})


@app.route('/uploads/images/<filename>')
def uploaded_image(filename):
    return send_from_directory(UPLOAD_FOLDER_IMAGES, filename)


@app.route('/uploads/detected/<filename>')
def detected_image(filename):
    return send_from_directory(UPLOAD_FOLDER_DETECTED, filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)