from flask import Flask, request, render_template, redirect, url_for, session, g
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "admin":
            session['user'] = 'admin'
            return redirect(url_for('admin_index'))
        elif username == "user" and password == "user":
            session['user'] = 'user'
            return redirect(url_for('user_index'))
        else:
            return "Credenziali non valide, riprovare!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_index():
    if 'user' in session and session['user'] == 'admin':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = {shoe['id']: db.execute('SELECT * FROM reviews WHERE shoe_id = ?', (shoe['id'],)).fetchall() for shoe in shoes}
        if request.method == 'POST':
            if 'add_shoe' in request.form:
                name = request.form['name']
                description = request.form['description']
                db.execute('INSERT INTO shoes (name, description) VALUES (?, ?)', (name, description))
                db.commit()
            elif 'delete_shoe' in request.form:
                shoe_id = request.form['shoe_id']
                db.execute('DELETE FROM shoes WHERE id = ?', (shoe_id,))
                db.execute('DELETE FROM reviews WHERE shoe_id = ?', (shoe_id,))
                db.commit()
            elif 'delete_review' in request.form:
                review_id = request.form['review_id']
                db.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
                db.commit()
        db.close()
        return render_template('admin_index.html', shoes=shoes, reviews=reviews)
    return redirect(url_for('login'))


@app.route('/user', methods=['GET', 'POST'])
def user_index():
    if 'user' in session and session['user'] == 'user':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = {shoe['id']: db.execute('SELECT * FROM reviews WHERE shoe_id = ?', (shoe['id'],)).fetchall() for shoe in shoes}
        db.close()
        return render_template('user_index.html', shoes=shoes, reviews=reviews)
    return redirect(url_for('login'))

@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user' in session and session['user'] == 'user':
        shoe_id = request.form['shoe_id']
        review_text = request.form['review_text']
        rating = request.form['rating']
        if shoe_id and review_text and rating.isdigit() and 0 <= int(rating) <= 5:
            db = get_db_connection()
            db.execute('INSERT INTO reviews (shoe_id, review_text, rating) VALUES (?, ?, ?)', 
                       (shoe_id, review_text, int(rating)))
            db.commit()
            db.close()
        return redirect(url_for('user_index'))

if __name__ == '__main__':
    app.run(debug=True)
