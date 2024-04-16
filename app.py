from flask import Flask, request, render_template, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

DATABASE = 'shoes.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    shoes_db = db.execute('SELECT * FROM shoes').fetchall()
    shoes = [dict(shoe) for shoe in shoes_db]
    db.close()
    return render_template('home.html', shoes=shoes)

@app.route('/search_shoes', methods=['GET'])
def search_shoes():
    query = request.args.get('query', '')
    db = get_db_connection()
    shoes = db.execute("SELECT * FROM shoes WHERE name LIKE ? OR description LIKE ?", ('%'+query+'%', '%'+query+'%')).fetchall()
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
            flash('Username already taken!')
            return render_template('register.html')
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
        flash('Invalid username or password')
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
        db.close()
        return render_template('admin_index.html', shoes=shoes)
    return redirect(url_for('login'))

@app.route('/add_shoe', methods=['POST'])
def add_shoe():
    if 'user' in session and session['role'] == 'admin':
        name = request.form['name']
        description = request.form['description']
        image = request.files['image']

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = filename  # il nome del file sarà sufficiente se è nella cartella 'static'
        else:
            image_url = 'default.jpg'  # Assicurati che questo file esista nella cartella 'static/images'

        db = get_db_connection()
        db.execute('INSERT INTO shoes (name, description, image_url) VALUES (?, ?, ?)', 
                   (name, description, image_url))
        db.commit()
        db.close()
        
        flash('Scarpa aggiunta con successo.')
        return redirect(url_for('admin_index'))
    else:
        flash('Devi essere amministratore per aggiungere scarpe.')
        return redirect(url_for('login'))




@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    shoe_id = request.form['shoe_id']
    review_text = request.form['review_text']
    rating = request.form['rating']

    db = get_db_connection()
    db.execute('INSERT INTO reviews (shoe_id, user_id, review_text, rating) VALUES (?, ?, ?, ?)',
               (shoe_id, user_id, review_text, rating))
    db.commit()
    db.close()

    return redirect(url_for('user_index'))


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

@app.route('/user', methods=['GET', 'POST'])
def user_index():
    if 'user' in session and session['role'] == 'user':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        reviews = {}
        for shoe in shoes:
            shoe_reviews = db.execute('SELECT * FROM reviews WHERE shoe_id = ?', (shoe['id'],)).fetchall()
            reviews[shoe['id']] = shoe_reviews
        db.close()
        return render_template('user_index.html', shoes=shoes, reviews=reviews)
    return redirect(url_for('login'))

@app.route('/edit_shoe/<int:shoe_id>', methods=['GET'])
def edit_shoe(shoe_id):
    db = get_db_connection()
    shoe = db.execute('SELECT * FROM shoes WHERE id = ?', (shoe_id,)).fetchone()
    db.close()
    if shoe:
        return render_template('edit_shoe.html', shoe=shoe)
    return redirect(url_for('admin_index'))

@app.route('/update_shoe/<int:shoe_id>', methods=['POST'])
def update_shoe(shoe_id):
    name = request.form['name']
    description = request.form['description']
    image = request.files.get('image')
    
    db = get_db_connection()
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.execute('UPDATE shoes SET name = ?, description = ?, image_url = ? WHERE id = ?',
                   (name, description, filename, shoe_id))
    else:
        db.execute('UPDATE shoes SET name = ?, description = ? WHERE id = ?',
                   (name, description, shoe_id))
    db.commit()
    db.close()
    
    return redirect(url_for('admin_index'))


if __name__ == '__main__':
    app.run(debug=True)
