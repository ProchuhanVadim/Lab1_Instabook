import sqlite3
import os
import datetime
import secrets
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'instabook-ultra-key'

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


def get_db_connection():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE,
                  password TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  gender TEXT,
                  birthday TEXT,
                  address TEXT)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS posts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  content TEXT,
                  user_id INTEGER,
                  date TEXT)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS comments 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  user_id INTEGER,
                  content TEXT,
                  date TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS password_resets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT,
                  token TEXT UNIQUE,
                  used INTEGER DEFAULT 0,
                  created_at TEXT)''')

    conn.commit()
    conn.close()


class User(UserMixin):
    def __init__(self, id, email, first_name, last_name):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if user:
        return User(user['id'], user['email'], user['first_name'], user['last_name'])
    return None


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('signup'))

    conn = get_db_connection()

    posts = conn.execute('''SELECT posts.*, users.first_name, users.last_name 
                            FROM posts
                            JOIN users ON posts.user_id = users.id 
                            ORDER BY posts.id DESC''').fetchall()

    comments = conn.execute('''SELECT comments.*, users.first_name, users.last_name
                               FROM comments
                               JOIN users ON comments.user_id = users.id
                               ORDER BY comments.id ASC''').fetchall()

    conn.close()

    return render_template('index.html', posts=posts, comments=comments)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['email'], user['first_name'], user['last_name'])
            login_user(user_obj)
            return redirect(url_for('index'))

        flash('Невірний логін або пароль')

    return render_template('sign-in.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = generate_password_hash(request.form.get('password'))

        try:
            conn = get_db_connection()
            cur = conn.execute(
                'INSERT INTO users (email, password, first_name, last_name) VALUES (?, ?, ?, ?)',
                (email, password, first_name, last_name)
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()

            login_user(User(new_id, email, first_name, last_name))
            return redirect(url_for('index'))

        except sqlite3.IntegrityError:
            flash('Користувач із таким email вже існує')

    return render_template('sign-up.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()

    if request.method == 'POST':
        conn.execute(
            '''UPDATE users
               SET first_name = ?, last_name = ?, gender = ?, birthday = ?, address = ?
               WHERE id = ?''',
            (
                request.form.get('first_name'),
                request.form.get('last_name'),
                request.form.get('gender'),
                request.form.get('birthday'),
                request.form.get('address'),
                current_user.id
            )
        )
        conn.commit()

    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()

    return render_template('account-editing.html', user=user_data)


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO posts (title, content, user_id, date) VALUES (?, ?, ?, ?)',
            (
                request.form.get('title'),
                request.form.get('content'),
                current_user.id,
                datetime.datetime.now().strftime("%d.%m.%Y")
            )
        )
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('posting.html')


@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    content = request.form.get('comment')

    if content:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO comments (post_id, user_id, content, date) VALUES (?, ?, ?, ?)',
            (
                post_id,
                current_user.id,
                content,
                datetime.datetime.now().strftime("%d.%m.%Y")
            )
        )
        conn.commit()
        conn.close()

    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user:
            token = secrets.token_urlsafe(32)
            created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            conn.execute(
                'INSERT INTO password_resets (email, token, created_at) VALUES (?, ?, ?)',
                (email, token, created_at)
            )
            conn.commit()

            reset_link = url_for('reset_password_token', token=token, _external=True)

            flash(f'Посилання для скидання пароля: <a href="{reset_link}">Скинути пароль</a>')
        else:
            flash('Користувача з таким email не знайдено.')

        conn.close()

    return render_template('forgot-password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    conn = get_db_connection()

    reset_request = conn.execute(
        'SELECT * FROM password_resets WHERE token = ? AND used = 0',
        (token,)
    ).fetchone()

    if not reset_request:
        conn.close()
        flash('Посилання для скидання пароля недійсне або вже використане.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        hashed_password = generate_password_hash(new_password)

        conn.execute(
            'UPDATE users SET password = ? WHERE email = ?',
            (hashed_password, reset_request['email'])
        )

        conn.execute(
            'UPDATE password_resets SET used = 1 WHERE token = ?',
            (token,)
        )

        conn.commit()
        conn.close()

        flash('Пароль успішно змінено. Увійдіть із новим паролем.')
        return redirect(url_for('login'))

    conn.close()
    return render_template('reset-password.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)