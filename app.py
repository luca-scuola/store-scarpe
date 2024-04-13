from flask import Flask, request, render_template, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'shoes.db'

def get_db_connection():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    db = get_db_connection()
    shoes = db.execute('SELECT * FROM shoes').fetchall()
    db.close()
    return render_template('home.html', shoes=shoes)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hash = generate_password_hash(password)
        db = get_db_connection()
        try:
            db.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, hash, 'user'))
            db.commit()
        except sqlite3.IntegrityError:
            db.close()
            return "Username already taken!"
        finally:
            db.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_index'))
            else:
                return redirect(url_for('user_index'))
        return "Invalid username or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_index():
    if 'user' in session and session['role'] == 'admin':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = {}
        for shoe in shoes:
            reviews[shoe['id']] = db.execute('SELECT * FROM reviews WHERE shoe_id = ?', (shoe['id'],)).fetchall()
        db.close()
        return render_template('admin_index.html', shoes=shoes, reviews=reviews)
    return redirect(url_for('login'))

@app.route('/delete_shoe', methods=['POST'])
def delete_shoe():
    if 'user' in session and session['role'] == 'admin':
        shoe_id = request.form.get('shoe_id')
        db = get_db_connection()
        db.execute('DELETE FROM shoes WHERE id = ?', (shoe_id,))
        db.commit()
        db.close()
        return redirect(url_for('admin_index'))
    return redirect(url_for('login'))

@app.route('/delete_review', methods=['POST'])
def delete_review():
    if 'user' in session and session['role'] == 'admin':
        review_id = request.form.get('review_id')
        db = get_db_connection()
        db.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        db.commit()
        db.close()
        return redirect(url_for('admin_index'))
    return redirect(url_for('login'))

@app.route('/user', methods=['GET', 'POST'])
def user_index():
    if 'user' in session and session['role'] == 'user':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = db.execute('SELECT * FROM reviews').fetchall()
        db.close()
        return render_template('user_index.html', shoes=shoes, reviews=reviews)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
