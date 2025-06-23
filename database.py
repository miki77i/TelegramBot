import sqlite3
import os
import json

DATA_FILE = 'database'

def create_connection(db_file='database.py'):
    """ подключение к бд SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """Создает таблицу"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(e)

# Инициализация бд
conn = create_connection()
if conn is not None:
    create_table(conn)
    print("подкл к бд успешно")
    conn.close()
else:
    print("Невозможно создать подкл к бд")
    


# Добавление пользователя
def add_user(user_id, username, first_name, last_name):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()

# Получение пользователя по user_id
def get_user(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            user = cursor.fetchone()
            return user
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()
    return None

#сохранение сообщений
def save_message_to_db(user_id, text):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO messages (user_id, text) VALUES (?, ?)",
            (user_id, text)
        )
        conn.commit()
    finally:
        conn.close()

#загружение файлов
def load_data():
        conn = sqlite3.connect(DATA_FILE)
        cursor = conn.cursor()
        # Загружаем пользователей
        cursor.execute("SELECT user_id, data FROM users")
        users = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    
        # Загружаем пары
        cursor.execute("SELECT pair_id, data FROM pairs")
        pairs = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    
        conn.close()
    
        return {
            "users": users,
            "pairs": pairs
        }
    

#сохранение данных
def save_data(data):
        #Сохранение всех данных в базу данных
        conn = sqlite3.connect(DATA_FILE)
        cursor = conn.cursor()
    
        # Очищаем таблицы перед сохранением
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM pairs")
        
        # Сохраняем пользователей
        for user_id, user_data in data["users"].items():
            cursor.execute(
                "INSERT INTO users (user_id, data) VALUES (?, ?)",
                (user_id, json.dumps(user_data, ensure_ascii=False))
            )
        
        # Сохраняем пары
        for pair_id, pair_data in data["pairs"].items():
            cursor.execute(
                "INSERT INTO pairs (pair_id, data) VALUES (?, ?)",
                (pair_id, json.dumps(pair_data, ensure_ascii=False))
            )
        
        conn.commit()
        conn.close()

#zfdf
