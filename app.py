from flask import Flask, request, render_template, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os


app = Flask(__name__)
app.secret_key = 'key'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg'}


DATABASE = 'shoes.db'


# Funzione per verificare se l'estensione del file è consentita
def allowed_file(filename):
    # Verifico se l'estensione del file è consentita confrontando l'estensione del file con un insieme di estensioni consentite
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Funzione per ottenere una connessione al database
def get_db_connection():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Imposto il tipo di riga restituito come oggetto sqlite3.Row per poter accedere ai risultati delle query
        db.row_factory = sqlite3.Row
    return db


# Funzione per chiudere la connessione al database quando non è più necessaria
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Route per la pagina principale, reindirizza alla home
@app.route('/')
def index():
    return redirect(url_for('home'))


# Route per la pagina home, mostra le informazioni sulle scarpe
@app.route('/home')
def home():
    db = get_db_connection()
    shoes_db = db.execute('SELECT * FROM shoes').fetchall()
    # Trasformo ogni riga del risultato della query in un dizionario
    shoes = [dict(shoe) for shoe in shoes_db]
    db.close()
    return render_template('home.html', shoes=shoes)


# Route per la registrazione di un nuovo utente
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


# Route per il login degli utenti
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


# Route per il logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# Route per la pagina admin, mostra le informazioni sulle scarpe e le recensioni associate
@app.route('/admin', methods=['GET', 'POST'])
def admin_index():
    if 'user' in session and session['role'] == 'admin':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        # Inizializzo una lista vuota per memorizzare i dati delle scarpe con le recensioni associate
        shoes_data = []
        for shoe in shoes:
            # Prendo le recensioni associate a questa scarpa
            reviews = db.execute('SELECT r.review_text, u.username, r.id FROM reviews r JOIN users u ON r.user_id = u.id WHERE r.shoe_id = ?', (shoe['id'],)).fetchall()
            # Aggiungo i dettagli della scarpa e le recensioni associate alla lista shoes_data
            shoes_data.append({
                'id': shoe['id'],  
                'name': shoe['name'],  
                'description': shoe['description'],  
                'price': shoe['price'], 
                'image_url': shoe['image_url'],  
                'reviews': reviews  
            })
        db.close()
        return render_template('admin_index.html', shoes=shoes_data)
    return redirect(url_for('login'))


# Route per l'aggiunta di una nuova scarpa
@app.route('/add_shoe', methods=['POST'])
def add_shoe():
    if 'user' in session and session['role'] == 'admin':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.files['image']

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = filename
        else:
            image_url = 'default.jpg'

        db = get_db_connection()
        db.execute('INSERT INTO shoes (name, description, price, image_url) VALUES (?, ?, ?, ?)', 
                   (name, description, price, image_url))
        db.commit()
        db.close()
        
        flash('Scarpa aggiunta con successo.')
        return redirect(url_for('admin_index'))
    else:
        flash('Devi essere amministratore per aggiungere scarpe.')
        return redirect(url_for('login'))


# Route per l'aggiunta di una recensione
@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    shoe_id = request.form['shoe_id']
    review_text = request.form['review_text']

    db = get_db_connection()
    db.execute('INSERT INTO reviews (shoe_id, user_id, review_text) VALUES (?, ?, ?)',
               (shoe_id, user_id, review_text))
    db.commit()
    db.close()

    return redirect(url_for('user_index'))


# Route per l'eliminazione di una scarpa
@app.route('/delete_shoe', methods=['POST'])
def delete_shoe():
    if 'user' in session and session['role'] == 'admin':
         # Ottengo l'ID della scarpa da eliminare
        shoe_id = request.form.get('shoe_id')
        db = get_db_connection()
        db.execute('DELETE FROM shoes WHERE id = ?', (shoe_id,))
        db.commit()
        db.close()
        return redirect(url_for('admin_index'))
    return redirect(url_for('login'))


# Route per la pagina principale degli utenti
@app.route('/user', methods=['GET', 'POST'])
def user_index():
    if 'user' in session and session['role'] == 'user':
        db = get_db_connection()
        shoes = db.execute('SELECT * FROM shoes').fetchall()
        # Inizializzo un dizionario vuoto per memorizzare le recensioni delle scarpe
        reviews = {}
        for shoe in shoes:
            # Ottengo le recensioni associate a questa scarpa
            shoe_reviews = db.execute('''
                SELECT r.*, u.username FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.shoe_id = ?
            ''', (shoe['id'],)).fetchall()
            # Assegno le recensioni alla scarpa utilizzando l'ID della scarpa come chiave nel dizionario reviews
            reviews[shoe['id']] = shoe_reviews
        db.close()
        # Passo le informazioni sulle scarpe e le recensioni per la visualizzazione
        return render_template('user_index.html', shoes=shoes, reviews=reviews, user_name=session.get('user', 'Guest'))
    return redirect(url_for('login'))


# Route per la modifica di una scarpa
@app.route('/edit_shoe/<int:shoe_id>', methods=['GET'])
def edit_shoe(shoe_id):
    db = get_db_connection()
    shoe = db.execute('SELECT * FROM shoes WHERE id = ?', (shoe_id,)).fetchone()
    db.close()
    # Se la scarpa è stata trovata
    if shoe:
        return render_template('edit_shoe.html', shoe=shoe)
    # Se la scarpa non è stata trovata
    return redirect(url_for('admin_index'))


# Route per l'aggiornamento delle informazioni di una scarpa
@app.route('/update_shoe/<int:shoe_id>', methods=['POST'])
 # Ottengo i nuovi dettagli della scarpa dalla richiesta POST
def update_shoe(shoe_id):
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image = request.files.get('image')
    
    db = get_db_connection()
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.execute('UPDATE shoes SET name = ?, description = ?, price = ?, image_url = ? WHERE id = ?',
                   (name, description, price, filename, shoe_id))
    # Se non è stata fornita un'immagine o l'estensione del file non è consentita, faccio l' execute senza l' immagine
    else:
        db.execute('UPDATE shoes SET name = ?, description = ?, price = ? WHERE id = ?',
                   (name, description, price, shoe_id))
    db.commit()
    db.close()
    
    return redirect(url_for('admin_index'))


# Route per l'aggiunta di una scarpa al carrello
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        flash('You need to login to add items to the cart.')
        return redirect(url_for('login'))

    # Ottengo l'ID della scarpa e l'ID dell'utente dal modulo POST
    shoe_id = request.form['shoe_id']
    user_id = session['user_id']

    db = get_db_connection()
    db.execute('INSERT INTO cart (user_id, shoe_id) VALUES (?, ?)', (user_id, shoe_id))
    db.commit()
    db.close()

    flash('Shoe added to cart successfully.')
    return redirect(url_for('user_index'))


# Route per la visualizzazione del carrello
@app.route('/view_cart')
def view_cart():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Ottengo l'ID dell'utente dalla sessione
    user_id = session['user_id']
    db = get_db_connection()
    # Ottengo tutte le righe del carrello per l'utente corrente, inclusi i dettagli delle scarpe e le recensioni associate
    cart_items = db.execute('''
        SELECT s.*, c.id AS cart_id, r.review_text, r.user_id AS reviewer_id, u.username AS reviewer_name
        FROM cart c
        JOIN shoes s ON c.shoe_id = s.id
        LEFT JOIN reviews r ON s.id = r.shoe_id
        JOIN users u ON r.user_id = u.id
        WHERE c.user_id = ?
    ''', (user_id,)).fetchall()
    db.close()

    # Creo un dizionario per organizzare le scarpe del carrello
    organized_items = {}
    for item in cart_items:
         # Controllo se l'ID della scarpa è già presente nel dizionario organized_items
        if item['id'] in organized_items:
            # Se l'ID è già presente, aggiungo la recensione associata alla scarpa
            organized_items[item['id']]['reviews'].append({
                'text': item['review_text'],
                'username': item['reviewer_name']
            })
        # Se l'ID non è presente, creo una nuova voce nel dizionario per questa scarpa
        else:
            organized_items[item['id']] = {
                'name': item['name'],
                'description': item['description'],
                'price': item['price'],
                'image_url': item['image_url'],
                'id': item['id'],
                # Se c'è una recensione associata la aggiungo, altrimenti creo una lista vuota per le recensioni
                'reviews': [{
                    'text': item['review_text'],
                    'username': item['reviewer_name']
                }] if item['review_text'] else []
            }
    
    # Passo i dati organizzati del carrello 
    return render_template('cart.html', cart_items=list(organized_items.values()))


# Route per la ricerca di scarpe
@app.route('/search')
def search():
     # Ottengo il parametro di ricerca dalla richiesta GET e lo assegno alla variabile "query". Se il parametro non è specificato imposto "query" a una stringa vuota.
    query = request.args.get('query', '')
    # Controllo se è stata data una query
    if query:
        db = get_db_connection()
        results = db.execute('SELECT * FROM shoes WHERE name LIKE ?', ('%' + query + '%',)).fetchall()
        # Inizializzo un dizionario per memorizzare le recensioni associate a ciascuna scarpa nei risultati della ricerca
        reviews = {}
        for shoe in results:
            shoe_reviews = db.execute('''
                SELECT r.*, u.username FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.shoe_id = ?
            ''', (shoe['id'],)).fetchall()
            # Salvo le recensioni in base all'ID della scarpa nel dizionario delle recensioni
            reviews[shoe['id']] = shoe_reviews
        db.close()
        # Passo le scarpe trovate e le recensioni associate
        return render_template('user_index.html', shoes=results, reviews=reviews, user_name=session.get('user', 'Guest'))
    else:
        return redirect(url_for('user_index'))


# Route per l'eliminazione di una recensione
@app.route('/delete_review', methods=['POST'])
def delete_review():
    if 'user' in session and session['role'] == 'admin':
        # Ottengo l'ID della recensione dalla richiesta POST
        review_id = request.form.get('review_id')
        try:
            db = get_db_connection()
            db.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
            db.commit()
        except Exception as e:
             # In caso di errore faccio il rollback delle modifiche
            db.rollback()
            flash('Failed to delete review.')
        finally:
            db.close()
            flash('Review deleted successfully.')
        return redirect(url_for('admin_index'))
    else:
        flash('Unauthorized access.')
    return redirect(url_for('login'))


# Route per rimuovere una scarpa dal carrello
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user' not in session:
        flash('You need to login to manage the cart.')
        return redirect(url_for('login'))

    # Ottengo l'ID della scarpa e l'ID dell'utente dalla richiesta POST
    shoe_id = request.form['shoe_id']
    user_id = session['user_id']

    try:
        db = get_db_connection()
        result = db.execute('DELETE FROM cart WHERE user_id = ? AND shoe_id = ?', (user_id, shoe_id))
        db.commit()
        # Controllo se è stata eliminata una riga dalla tabella del carrello
        if result.rowcount == 0:
            flash('No item was removed. Check if the item ID is correct and belongs to the user.')
        else:
            # Se una riga è stata eliminata, mostro un messaggio di conferma
            flash('Shoe removed from cart successfully.')
    except Exception as e:
        # In caso di errore, eseguo il rollback delle modifiche
        db.rollback()
        flash(f'An error occurred: {str(e)}')
    finally:
        db.close()

    return redirect(url_for('view_cart'))


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/refund')
def refund():
    return render_template('refund.html')


@app.route('/shipping')
def shipping():
    return render_template('shipping.html')


if __name__ == '__main__':
    app.run(debug=True)