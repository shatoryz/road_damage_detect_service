from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Разрешенные типы файлов
ALLOWED_EXTENSIONS = {'image/*', 'csv'}


# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('input.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'fileToUpload' not in request.files:
        return 'Файл не выбран!'

    file = request.files['fileToUpload']

    if file.filename == '':
        return 'Файл не выбран!'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # безопасное имя
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return f'Файл {filename} успешно загружен!'

    return 'Файл не поддерживается!'


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=8080)
