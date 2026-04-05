import sqlite3
import os

DB_FILE = "bot.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def show_menu():
    print("\n===== УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ =====")
    print("1. Показать статистику")
    print("2. Показать всех участников")
    print("3. Показать все предложения")
    print("4. Удалить ВСЕ предложения")
    print("5. Удалить ВСЕХ участников")
    print("6. Удалить конкретного участника по номеру")
    print("7. Сбросить статус предложения у участника")
    print("8. Удалить конкретного участника и его предложение")
    print("0. Выход")
    print("=" * 40)

def show_stats():
    conn = get_db()
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    subs = c.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    has_sub = c.execute("SELECT COUNT(*) FROM users WHERE has_submission = 1").fetchone()[0]
    print(f"\n👥 Участников: {total}")
    print(f"📝 Предложений: {subs}")
    print(f"✅ Подавших: {has_sub}")
    conn.close()

def show_users():
    conn = get_db()
    c = conn.cursor()
    users = c.execute("SELECT * FROM users").fetchall()
    if not users:
        print("\nНет участников")
    else:
        print(f"\n👥 Участники ({len(users)}):")
        for u in users:
            status = "✅" if u["has_submission"] else "⏳"
            print(f"  {status} Номер: {u['number']} | ID: {u['user_id']} | Дата: {u['registered_at']}")
    conn.close()

def show_submissions():
    conn = get_db()
    c = conn.cursor()
    subs = c.execute("SELECT * FROM submissions").fetchall()
    if not subs:
        print("\nНет предложений")
    else:
        print(f"\n📝 Предложения ({len(subs)}):")
        for s in subs:
            print(f"  [{s['timestamp']}] #{s['number']} | {s['direction']}: {s['proposal'][:50]}...")
    conn.close()

def clear_submissions():
    confirm = input("\nУдалить ВСЕ предложения? (да/нет): ")
    if confirm.lower() == "да":
        conn = get_db()
        conn.execute("DELETE FROM submissions")
        conn.execute("UPDATE users SET has_submission = 0")
        conn.commit()
        conn.close()
        print("✅ Все предложения удалены")
    else:
        print("Отменено")

def clear_users():
    confirm = input("\nУдалить ВСЕХ участников? Это действие необратимо! (да/нет): ")
    if confirm.lower() == "да":
        confirm2 = input("Точно удалить ВСЕХ? (да/нет): ")
        if confirm2.lower() == "да":
            conn = get_db()
            conn.execute("DELETE FROM submissions")
            conn.execute("DELETE FROM users")
            conn.commit()
            conn.close()
            print("✅ Все участники удалены")
        else:
            print("Отменено")
    else:
        print("Отменено")

def delete_user_by_number():
    number = input("\nВведите номер участника: ")
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE number = ?", (number,)).fetchone()
    if user:
        c.execute("DELETE FROM submissions WHERE number = ?", (number,))
        c.execute("DELETE FROM users WHERE number = ?", (number,))
        conn.commit()
        conn.close()
        print(f"✅ Участник #{number} удалён")
    else:
        print("Участник не найден")
        conn.close()

def reset_submission():
    number = input("\nВведите номер участника для сброса статуса: ")
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET has_submission = 0 WHERE number = ?", (number,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    if affected > 0:
        print(f"✅ Статус участника #{number} сброшен — может подать предложение заново")
    else:
        print("Участник не найден")

def delete_user_and_submission():
    number = input("\nВведите номер участника для полного удаления: ")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM submissions WHERE number = ?", (number,))
    c.execute("DELETE FROM users WHERE number = ?", (number,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    if affected > 0:
        print(f"✅ Участник #{number} и его предложение удалены")
    else:
        print("Участник не найден")

def main():
    if not os.path.exists(DB_FILE):
        print("База данных не найдена. Запустите бота сначала.")
        return

    while True:
        show_menu()
        choice = input("\nВыбор: ").strip()

        if choice == "1":
            show_stats()
        elif choice == "2":
            show_users()
        elif choice == "3":
            show_submissions()
        elif choice == "4":
            clear_submissions()
        elif choice == "5":
            clear_users()
        elif choice == "6":
            delete_user_by_number()
        elif choice == "7":
            reset_submission()
        elif choice == "8":
            delete_user_and_submission()
        elif choice == "0":
            print("Выход")
            break
        else:
            print("Неверный выбор")

if __name__ == "__main__":
    main()
