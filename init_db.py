import sqlite3
import os

DATABASE = 'shoes.db'

def initialize_database():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        with open("shoes.sql", "r") as f:
            cursor.executescript(f.read())
        conn.commit()
    except Exception as e:
        print("Failed to initialize the database:", e)
    finally:
        conn.close()




if __name__ == "__main__":
    print("Current directory:", os.getcwd())
    initialize_database()
