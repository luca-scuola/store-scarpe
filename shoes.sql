-- Creazione della tabella per le scarpe
CREATE TABLE IF NOT EXISTS shoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT DEFAULT 'default.jpg'  -- Nome dell'immagine predefinita se non specificato
);


-- Creazione della tabella per gli utenti
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
);

-- Modifying the creation of the reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shoe_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    review_text TEXT NOT NULL,
    FOREIGN KEY(shoe_id) REFERENCES shoes(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    shoe_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (shoe_id) REFERENCES shoes(id)
);


