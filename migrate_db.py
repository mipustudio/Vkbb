import sqlite3
conn = sqlite3.connect('bot.db')
c = conn.cursor()

# Проверяем текущие колонки
cols = [row[1] for row in c.execute('PRAGMA table_info(users)').fetchall()]
print(f"Текущие колонки: {cols}")

# 1. Добавляем current_direction_index
if 'current_direction_index' not in cols:
    c.execute('ALTER TABLE users ADD COLUMN current_direction_index INTEGER DEFAULT 0')
    print("  + Добавлена колонка current_direction_index")
else:
    print("  - current_direction_index уже существует")

# 2. Переносим данные из has_submission
if 'has_submission' in cols:
    c.execute('UPDATE users SET current_direction_index = 5 WHERE has_submission = 1 AND current_direction_index = 0')
    print(f"  + Перенесено: {c.rowcount} участников (has_submission=1 -> current_direction_index=5)")

# 3. Удаляем has_submission (пересоздаём таблицу без неё)
if 'has_submission' in cols:
    c.execute("""
        CREATE TABLE IF NOT EXISTS users_new (
            user_id INTEGER PRIMARY KEY,
            number TEXT UNIQUE NOT NULL,
            registered_at TEXT NOT NULL,
            current_direction_index INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        INSERT INTO users_new (user_id, number, registered_at, current_direction_index)
        SELECT user_id, number, registered_at, COALESCE(current_direction_index, 0)
        FROM users
    """)
    c.execute("DROP TABLE users")
    c.execute("ALTER TABLE users_new RENAME TO users")
    print("  - Удалена колонка has_submission (пересоздана таблица)")

conn.commit()

# Проверка
cols = [row[1] for row in c.execute('PRAGMA table_info(users)').fetchall()]
print(f"\nИтоговые колонки: {cols}")
rows = c.execute('SELECT * FROM users').fetchall()
print(f"Данные: {rows}")
conn.close()
print("\nМиграция завершена!")
