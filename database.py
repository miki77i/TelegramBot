import sqlite3

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

#zfdf