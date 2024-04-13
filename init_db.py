import sqlite3

DATABASE = 'shoes.db'

def initialize_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    with open("shoes.sql", "r") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()
