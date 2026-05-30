"""Сброс логина и пароля администратора."""
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

DB_NAME = "triumph_gym.db"
USERNAME = "admin"
PASSWORD = "admin123"


def main():
    password_hash = generate_password_hash(PASSWORD, method="pbkdf2:sha256")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        existing = cursor.execute(
            "SELECT id FROM admins WHERE username = ?", (USERNAME,)
        ).fetchone()
        if existing:
            cursor.execute(
                "UPDATE admins SET password_hash = ? WHERE username = ?",
                (password_hash, USERNAME),
            )
            print("Пароль администратора обновлён.")
        else:
            cursor.execute(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                (USERNAME, password_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            print("Администратор создан.")
        conn.commit()
    print(f"Логин: {USERNAME}")
    print(f"Пароль: {PASSWORD}")
    print("Откройте: http://127.0.0.1:5000/login")


if __name__ == "__main__":
    main()
