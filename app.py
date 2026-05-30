import sqlite3
from datetime import datetime


DB_NAME = "triumph_gym.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trainers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                specialization TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                duration_days INTEGER NOT NULL,
                price REAL NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                membership_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY(client_id) REFERENCES clients(id),
                FOREIGN KEY(membership_id) REFERENCES memberships(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                trainer_id INTEGER,
                visit_date TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id),
                FOREIGN KEY(trainer_id) REFERENCES trainers(id)
            )
            """
        )
        conn.commit()


def input_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            print("Неверный формат даты. Используйте YYYY-MM-DD.")


def add_client():
    full_name = input("ФИО клиента: ").strip()
    phone = input("Телефон: ").strip()
    email = input("Email (необязательно): ").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO clients (full_name, phone, email, created_at) VALUES (?, ?, ?, ?)",
                (full_name, phone, email if email else None, created_at),
            )
            conn.commit()
            print("Клиент успешно добавлен.")
        except sqlite3.IntegrityError:
            print("Ошибка: клиент с таким телефоном уже существует.")


def list_clients():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, phone, email, created_at FROM clients ORDER BY id")
        rows = cursor.fetchall()

    if not rows:
        print("Список клиентов пуст.")
        return

    print("\n--- Клиенты ---")
    for row in rows:
        print(f"ID: {row[0]} | {row[1]} | Тел: {row[2]} | Email: {row[3] or '-'} | Создан: {row[4]}")


def add_trainer():
    full_name = input("ФИО тренера: ").strip()
    specialization = input("Специализация: ").strip()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO trainers (full_name, specialization) VALUES (?, ?)",
            (full_name, specialization),
        )
        conn.commit()
        print("Тренер добавлен.")


def list_trainers():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, specialization FROM trainers ORDER BY id")
        rows = cursor.fetchall()

    if not rows:
        print("Тренеры отсутствуют.")
        return

    print("\n--- Тренеры ---")
    for row in rows:
        print(f"ID: {row[0]} | {row[1]} | Специализация: {row[2]}")


def add_membership_type():
    name = input("Название абонемента: ").strip()
    duration_days = input("Срок действия (дней): ").strip()
    price = input("Цена: ").strip()

    try:
        duration_days = int(duration_days)
        price = float(price)
    except ValueError:
        print("Ошибка: срок должен быть числом, цена - числом.")
        return

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO memberships (name, duration_days, price) VALUES (?, ?, ?)",
                (name, duration_days, price),
            )
            conn.commit()
            print("Тип абонемента добавлен.")
        except sqlite3.IntegrityError:
            print("Ошибка: абонемент с таким названием уже существует.")


def list_membership_types():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, duration_days, price FROM memberships ORDER BY id")
        rows = cursor.fetchall()

    if not rows:
        print("Список абонементов пуст.")
        return

    print("\n--- Типы абонементов ---")
    for row in rows:
        print(f"ID: {row[0]} | {row[1]} | {row[2]} дней | {row[3]:.2f} руб.")


def assign_membership_to_client():
    list_clients()
    client_id = input("\nID клиента: ").strip()
    list_membership_types()
    membership_id = input("\nID абонемента: ").strip()
    start_date = input_date("Дата начала (YYYY-MM-DD): ")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT duration_days FROM memberships WHERE id = ?", (membership_id,))
        membership = cursor.fetchone()

        if not membership:
            print("Ошибка: абонемент не найден.")
            return

        duration = membership[0]
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = start_dt.fromordinal(start_dt.toordinal() + duration)
        end_date = end_dt.strftime("%Y-%m-%d")

        cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
        client_exists = cursor.fetchone()
        if not client_exists:
            print("Ошибка: клиент не найден.")
            return

        cursor.execute(
            """
            INSERT INTO client_memberships (client_id, membership_id, start_date, end_date)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, membership_id, start_date, end_date),
        )
        conn.commit()
        print(f"Абонемент назначен. Действует до {end_date}.")


def list_client_memberships():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT cm.id, c.full_name, m.name, cm.start_date, cm.end_date
            FROM client_memberships cm
            JOIN clients c ON c.id = cm.client_id
            JOIN memberships m ON m.id = cm.membership_id
            ORDER BY cm.id
            """
        )
        rows = cursor.fetchall()

    if not rows:
        print("Назначенных абонементов пока нет.")
        return

    print("\n--- Активные/исторические абонементы клиентов ---")
    for row in rows:
        print(f"ID: {row[0]} | {row[1]} | {row[2]} | {row[3]} -> {row[4]}")


def register_visit():
    list_clients()
    client_id = input("\nID клиента: ").strip()

    list_trainers()
    trainer_input = input("\nID тренера (или Enter, если без тренера): ").strip()
    trainer_id = trainer_input if trainer_input else None

    visit_date = input_date("Дата посещения (YYYY-MM-DD): ")
    note = input("Комментарий (необязательно): ").strip()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
        if not cursor.fetchone():
            print("Ошибка: клиент не найден.")
            return

        if trainer_id:
            cursor.execute("SELECT id FROM trainers WHERE id = ?", (trainer_id,))
            if not cursor.fetchone():
                print("Ошибка: тренер не найден.")
                return

        cursor.execute(
            """
            INSERT INTO attendance (client_id, trainer_id, visit_date, note)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, trainer_id, visit_date, note if note else None),
        )
        conn.commit()
        print("Посещение зарегистрировано.")


def attendance_report():
    date_from = input_date("Период с (YYYY-MM-DD): ")
    date_to = input_date("Период по (YYYY-MM-DD): ")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.id, c.full_name, COALESCE(t.full_name, '-'), a.visit_date, COALESCE(a.note, '-')
            FROM attendance a
            JOIN clients c ON c.id = a.client_id
            LEFT JOIN trainers t ON t.id = a.trainer_id
            WHERE a.visit_date BETWEEN ? AND ?
            ORDER BY a.visit_date
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()

    if not rows:
        print("За указанный период посещений не найдено.")
        return

    print("\n--- Отчет по посещаемости ---")
    for row in rows:
        print(f"ID: {row[0]} | Клиент: {row[1]} | Тренер: {row[2]} | Дата: {row[3]} | Комментарий: {row[4]}")


def print_menu():
    print(
        """
==============================
Триумф — тренажёрный зал
==============================
1. Добавить клиента
2. Показать клиентов
3. Добавить тренера
4. Показать тренеров
5. Добавить тип абонемента
6. Показать типы абонементов
7. Назначить абонемент клиенту
8. Показать абонементы клиентов
9. Зарегистрировать посещение
10. Отчет по посещаемости
0. Выход
"""
    )


def main():
    init_db()
    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            add_client()
        elif choice == "2":
            list_clients()
        elif choice == "3":
            add_trainer()
        elif choice == "4":
            list_trainers()
        elif choice == "5":
            add_membership_type()
        elif choice == "6":
            list_membership_types()
        elif choice == "7":
            assign_membership_to_client()
        elif choice == "8":
            list_client_memberships()
        elif choice == "9":
            register_visit()
        elif choice == "10":
            attendance_report()
        elif choice == "0":
            print("Выход из программы.")
            break
        else:
            print("Неизвестная команда. Попробуйте снова.")


if __name__ == "__main__":
    main()
