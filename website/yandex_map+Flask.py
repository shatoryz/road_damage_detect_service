from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'csv', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
init_db()

@app.route('/')
def index():
    return render_template('home.html')


@app.route("/mops_ico")
def mops_ico():
    return send_from_directory(
        directory=app.root_path,
        path="static/icons/mops_ico.jpg",
        mimetype="image/jpeg"
    )

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
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                           (name, email, password))
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


@app.route('/map', methods=['GET', 'POST'])
def map_page():
    if request.method == 'POST':
        if 'fileToUpload' not in request.files:
            return 'Файл не выбран!'
        file = request.files['fileToUpload']
        if file.filename == '':
            return 'Файл не выбран!'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return f'Файл {filename} успешно загружен!'
        return 'Файл не поддерживается!'
    return render_template('yandex_api.html')



@app.route('/input')
def input_page():
    return render_template('input.html')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
