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
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()
        hash = generate_password_hash(password)
        try:
            db.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, hash, 'user'))
            db.commit()
        except sqlite3.IntegrityError:
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
        print("Username inserito:", username)
        print("Password inserita:", password)
        db = get_db_connection()
        user = db.execute('SELECT users.username, users.password_hash, users.role, users.id FROM users WHERE username = ?', (username,)).fetchone()
        print("Utente nel database:", user)
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[3]
            session['user'] = user['username']
            session['role'] = user['role']
            if user[2] == 'admin':
                return redirect(url_for('admin_index'))
            else:
                return redirect(url_for('user_index'))
        else:
            print("Credenziali invalide")
            return "Invalid username or password"
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_index():
    if 'user' in session and session['role'] == 'admin':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = {}  # Aggiungi questa riga per inizializzare il dizionario delle recensioni
        for shoe in shoes:
            reviews[shoe['id']] = db.execute('SELECT * FROM reviews WHERE shoe_id = ?', (shoe['id'],)).fetchall()
        db.close()
        return render_template('admin_index.html', shoes=shoes, reviews=reviews)  # Passa anche le recensioni al template
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
