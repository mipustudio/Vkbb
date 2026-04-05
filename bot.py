import vk_api
from vk_api.utils import get_random_id
import requests
import time
import json
import os
import random
import sqlite3

# Настройки из переменных окружения (env)
TOKEN = os.environ.get("VK_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "237158911"))
API_VERSION = "5.199"
ADMIN_ID = int(os.environ.get("ADMIN_ID", "554458501"))
GOOGLE_SCRIPT_URL = os.environ.get("GOOGLE_SCRIPT_URL", "")

# База данных
DB_FILE = "bot.db"

# Темы
TOPICS = {
    "ОБУСТРОЙСТВО ТЕРРИТОРИИ": "Равный доступ к медицине, образованию, экологии и соц. инфраструктуре для всех регионов.",
    "ПРОИЗВОДИТЕЛЬНОСТЬ ТРУДА И КАДРЫ": "Инвестиции в подготовку кадров для промышленности и высокотехнологичных отраслей.",
    "ОБОРОННО-ТЕХНОЛОГИЧЕСКИЙ ВЫЗОВ": "Технологическая независимость и обороноспособность — фундамент национальной безопасности.",
    "ДЕМОГРАФИЧЕСКИЙ ВЫЗОВ": "Поддержка семьи, материнства и детства. Уверенность людей в завтрашнем дне.",
    "КУЛЬТУРНО-ЦЕННОСТНЫЙ ВЫЗОВ": "Культурный суверенитет, традиционные ценности и воспитание на примере собственных героев."
}

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

# Состояния пользователей
user_states = {}

# ==================== БАЗА ДАННЫХ ====================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Таблица настроек
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Таблица участников
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            number TEXT UNIQUE NOT NULL,
            registered_at TEXT NOT NULL,
            has_submission INTEGER DEFAULT 0
        )
    """)

    # Таблица предложений
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            number TEXT NOT NULL,
            direction TEXT NOT NULL,
            proposal TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Настройки по умолчанию
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('registration_enabled', 'true')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('submissions_enabled', 'false')")

    conn.commit()
    conn.close()
    print("  База данных инициализирована")

# ==================== КЛАВИАТУРЫ ====================

def get_start_keyboard():
    return {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "📝 Регистрация участника", "payload": {}}}],
            [{"action": {"type": "text", "label": "ℹ️ О боте", "payload": {}}}]
        ]
    }

def get_user_keyboard():
    return {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "📝 Подать предложение", "payload": {}}}],
            [{"action": {"type": "text", "label": "👤 Мой профиль", "payload": {}}},
             {"action": {"type": "text", "label": "ℹ️ Помощь", "payload": {}}}]
        ]
    }

def get_topics_keyboard():
    buttons = []
    for i, direction in enumerate(TOPICS.keys(), 1):
        buttons.append([{"action": {"type": "text", "label": f"{NUMBER_EMOJIS[i-1]} {direction}", "payload": {"topic": i}}}])
    return {"one_time": True, "buttons": buttons}

# ==================== УТИЛИТЫ ====================

def send_message(vk, peer_id, text, keyboard=None):
    try:
        params = {
            "peer_id": peer_id,
            "message": text,
            "random_id": get_random_id()
        }
        if keyboard:
            params["keyboard"] = json.dumps(keyboard)
        vk.messages.send(**params)
    except vk_api.exceptions.ApiError as e:
        print(f"  Ошибка отправки: {e}")

def send_to_google_sheets(data):
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=data, timeout=10)
        print(f"  Google Sheets: {response.status_code}")
        return True
    except Exception as e:
        print(f"  Ошибка Google Sheets: {e}")
        return False

# ==================== АДМИН КОМАНДЫ ====================

ADMIN_COMMANDS = ["/выкл рег", "/вкл рег", "/выкл пред", "/вкл пред", "/рассылка", "/роз", "/стат"]

def is_admin_command(text):
    text_lower = text.lower()
    for cmd in ADMIN_COMMANDS:
        if text_lower.startswith(cmd):
            return True
    return False

def handle_admin_command(vk, peer_id, text):
    conn = get_db()
    c = conn.cursor()
    text_lower = text.lower()

    if text_lower == "/выкл рег":
        c.execute("UPDATE settings SET value = 'false' WHERE key = 'registration_enabled'")
        conn.commit()
        conn.close()
        send_message(vk, peer_id, "🔴 Регистрация ВЫКЛЮЧЕНА")
        return

    if text_lower == "/вкл рег":
        c.execute("UPDATE settings SET value = 'true' WHERE key = 'registration_enabled'")
        conn.commit()
        conn.close()
        send_message(vk, peer_id, "🟢 Регистрация ВКЛЮЧЕНА")
        return

    if text_lower == "/выкл пред":
        c.execute("UPDATE settings SET value = 'false' WHERE key = 'submissions_enabled'")
        conn.commit()
        conn.close()
        send_message(vk, peer_id, "🔴 Приём предложений ВЫКЛЮЧЕН")
        return

    if text_lower == "/вкл пред":
        c.execute("UPDATE settings SET value = 'true' WHERE key = 'submissions_enabled'")
        conn.commit()
        conn.close()
        send_message(vk, peer_id, "🟢 Приём предложений ВКЛЮЧЁН")
        return

    if text_lower == "/стат":
        total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_submissions = c.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        has_submission = c.execute("SELECT COUNT(*) FROM users WHERE has_submission = 1").fetchone()[0]

        # По направлениям
        rows = c.execute("SELECT direction, COUNT(*) as cnt FROM submissions GROUP BY direction").fetchall()

        stat_text = f"📊 СТАТИСТИКА ФОРУМА\n\n"
        stat_text += f"👥 Участников: {total_users}\n"
        stat_text += f"✅ Подавших предложения: {has_submission}\n"
        stat_text += f"📝 Всего предложений: {total_submissions}\n\n"

        if rows:
            stat_text += "По направлениям:\n"
            for row in rows:
                stat_text += f"  • {row['direction']}: {row['cnt']}\n"

        conn.close()
        send_message(vk, peer_id, stat_text)
        return

    if text_lower.startswith("/рассылка"):
        message_text = text[len("/рассылка"):].strip()
        if not message_text:
            conn.close()
            send_message(vk, peer_id, "Использование: /рассылка текст сообщения")
            return

        users = c.execute("SELECT user_id FROM users").fetchall()
        conn.close()

        if len(users) == 0:
            send_message(vk, peer_id, "Нет зарегистрированных участников")
            return

        send_message(vk, peer_id, f"Отправка рассылки {len(users)} участникам...")
        sent = 0
        failed = 0
        for user in users:
            try:
                vk.messages.send(
                    peer_id=user["user_id"] + 2000000000,
                    message=f"📣 РАССЫЛКА\n\n{message_text}",
                    random_id=get_random_id(),
                    keyboard=json.dumps(get_user_keyboard())
                )
                sent += 1
            except:
                try:
                    vk.messages.send(
                        user_id=user["user_id"],
                        message=f"📣 РАССЫЛКА\n\n{message_text}",
                        random_id=get_random_id(),
                        keyboard=json.dumps(get_user_keyboard())
                    )
                    sent += 1
                except:
                    failed += 1
            time.sleep(0.3)

        send_message(vk, peer_id, f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")
        return

    if text_lower.startswith("/роз"):
        parts = text_lower.split()
        if len(parts) < 2:
            conn.close()
            send_message(vk, peer_id, "Использование: /роз количество\nНапример: /роз 5")
            return

        try:
            prizes_count = int(parts[1])
        except ValueError:
            conn.close()
            send_message(vk, peer_id, "Укажите число призов. Например: /роз 5")
            return

        if prizes_count < 1:
            conn.close()
            send_message(vk, peer_id, "Количество призов должно быть больше 0")
            return

        total = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if total < prizes_count:
            conn.close()
            send_message(vk, peer_id, f"Недостаточно участников! Зарегистрировано: {total}")
            return

        winners = c.execute("SELECT * FROM users ORDER BY RANDOM() LIMIT ?", (prizes_count,)).fetchall()
        conn.close()

        for i, winner in enumerate(winners, 1):
            try:
                vk.messages.send(
                    peer_id=winner["user_id"] + 2000000000,
                    message=(
                        f"🎉 ПОЗДРАВЛЯЕМ! 🎉\n\n"
                        f"Вы выиграли приз на форуме!\n\n"
                        f"Ваш номер: {winner['number']}\n"
                        f"Приз: {i}-е место\n\n"
                        f"Покажите это сообщение ведущему для получения приза!"
                    ),
                    random_id=get_random_id(),
                    keyboard=json.dumps(get_user_keyboard())
                )
            except:
                try:
                    vk.messages.send(
                        user_id=winner["user_id"],
                        message=(
                            f"🎉 ПОЗДРАВЛЯЕМ! 🎉\n\n"
                            f"Вы выиграли приз на форуме!\n\n"
                            f"Ваш номер: {winner['number']}\n"
                            f"Приз: {i}-е место\n\n"
                            f"Покажите это сообщение ведущему для получения приза!"
                        ),
                        random_id=get_random_id(),
                        keyboard=json.dumps(get_user_keyboard())
                    )
                except:
                    pass
            time.sleep(0.3)

        result_text = f"🏆 РОЗЫГРЫШ: {prizes_count} призов\n\n"
        for i, winner in enumerate(winners, 1):
            result_text += f"{i}. Номер {winner['number']} (ID: {winner['user_id']})\n"

        send_message(vk, peer_id, result_text)
        return

    conn.close()


# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

def handle_message(vk, user_id, peer_id, text):
    conn = get_db()
    c = conn.cursor()

    # Загружаем настройки
    settings = {}
    for row in c.execute("SELECT key, value FROM settings"):
        settings[row["key"]] = row["value"]

    reg_enabled = settings.get("registration_enabled", "true") == "true"
    sub_enabled = settings.get("submissions_enabled", "false") == "true"

    # Админ команды
    if user_id == ADMIN_ID and is_admin_command(text):
        conn.close()
        handle_admin_command(vk, peer_id, text)
        return

    # Проверяем регистрацию
    user = c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    # ========== НЕ ЗАРЕГИСТРИРОВАН ==========
    if not user:
        # Если ждём номер
        if user_id in user_states and user_states[user_id].get("step") == "waiting_number":
            number = text.strip()

            if not number.isdigit() or len(number) != 3:
                send_message(vk, peer_id,
                    "⚠️ Номер должен состоять из 3 цифр.\n\n"
                    "Введите корректный номер (например: 101, 201, 301):"
                )
                conn.close()
                return

            existing = c.execute("SELECT * FROM users WHERE number = ?", (number,)).fetchone()
            if existing:
                send_message(vk, peer_id,
                    "⚠️ Этот номер уже зарегистрирован!\n\n"
                    "Если это ваш номер — обратитесь к администратору."
                )
                conn.close()
                return

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO users (user_id, number, registered_at) VALUES (?, ?, ?)",
                     (user_id, number, now))
            conn.commit()

            del user_states[user_id]
            conn.close()

            send_message(vk, peer_id,
                f"✅ Регистрация завершена!\n\n"
                f"Ваш номер: {number}\n\n"
                f"Ожидайте сообщение от администратора форума.",
                keyboard=get_user_keyboard()
            )
            print(f"  Зарегистрирован: ID={user_id}, Номер={number}")
            return

        # Кнопки меню
        if text == "📝 Регистрация участника":
            if not reg_enabled:
                conn.close()
                send_message(vk, peer_id, "Регистрация временно недоступна.")
                return

            send_message(vk, peer_id,
                "📝 РЕГИСТРАЦИЯ\n\n"
                "Введите ваш идентификационный номер (3 цифры):"
            )
            user_states[user_id] = {"step": "waiting_number"}
            conn.close()
            return

        if text == "ℹ️ О боте":
            conn.close()
            send_message(vk, peer_id,
                "📖 О БОТЕ\n\n"
                "Это бот для сбора предложений на форуме.\n\n"
                "Порядок действий:\n"
                "1. Зарегистрируйтесь в боте\n"
                "2. Дождитесь уведомления от администратора\n"
                "3. Подайте предложение по выбранной теме\n\n"
                "По вопросам обратитесь к администратору.",
                keyboard=get_start_keyboard()
            )
            return

        # Первое сообщение
        conn.close()
        send_message(vk, peer_id,
            "👋 Добро пожаловать!\n\n"
            "Это бот для сбора предложений на форуме.\n\n"
            "Для участия необходимо зарегистрироваться.",
            keyboard=get_start_keyboard()
        )
        return

    # ========== ЗАРЕГИСТРИРОВАН ==========
    user_data = dict(user)

    if text == "📝 Подать предложение":
        if not sub_enabled:
            send_message(vk, peer_id,
                "Приём предложений временно закрыт.\n"
                "Ожидайте уведомление от администратора.",
                keyboard=get_user_keyboard()
            )
            conn.close()
            return

        if user_data["has_submission"]:
            send_message(vk, peer_id,
                "Вы уже подали предложение!\n\n"
                "Если хотите подать ещё одно — обратитесь к администратору.",
                keyboard=get_user_keyboard()
            )
            conn.close()
            return

        send_message(vk, peer_id,
            "📝 ПОДАЧА ПРЕДЛОЖЕНИЯ\n\n"
            "Выберите направление:",
            keyboard=get_topics_keyboard()
        )
        user_states[user_id] = {"step": "select_topic"}
        conn.close()
        return

    if text == "👤 Мой профиль":
        status = "✅ Предложение подано" if user_data["has_submission"] else "⏳ Ещё не подано"
        send_message(vk, peer_id,
            f"👤 ПРОФИЛЬ\n\n"
            f"Номер: {user_data['number']}\n"
            f"Зарегистрирован: {user_data['registered_at']}\n"
            f"Статус: {status}",
            keyboard=get_user_keyboard()
        )
        conn.close()
        return

    if text == "ℹ️ Помощь":
        send_message(vk, peer_id,
            "📖 ПОМОЩЬ\n\n"
            "Этот бот предназначен для сбора предложений от участников форума.\n\n"
            "Как подать предложение:\n"
            "1. Нажмите «Подать предложение»\n"
            "2. Выберите направление\n"
            "3. Напишите ваше предложение\n\n"
            "При возникновении проблем обратитесь к администратору.",
            keyboard=get_user_keyboard()
        )
        conn.close()
        return

    # Обработка состояний
    if user_id in user_states:
        state = user_states[user_id].get("step")

        if state == "select_topic":
            topics = list(TOPICS.keys())
            topic_index = -1

            try:
                topic_index = int(text) - 1
            except ValueError:
                for i, direction in enumerate(topics):
                    if direction in text:
                        topic_index = i
                        break

            if topic_index < 0 or topic_index >= len(topics):
                send_message(vk, peer_id, "Неверное направление. Выберите из кнопок:", keyboard=get_topics_keyboard())
                conn.close()
                return

            direction = topics[topic_index]
            user_states[user_id]["direction"] = direction
            user_states[user_id]["step"] = "waiting_proposal"

            send_message(vk, peer_id,
                f"Вы выбрали: {direction}\n\n"
                f"Описание: {TOPICS[direction]}\n\n"
                f"Напишите ваше предложение:"
            )
            conn.close()
            return

        if state == "waiting_proposal":
            direction = user_states[user_id]["direction"]
            now = time.strftime("%Y-%m-%d %H:%M:%S")

            # Сохраняем предложение
            c.execute("INSERT INTO submissions (user_id, number, direction, proposal, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (user_id, user_data["number"], direction, text, now))
            c.execute("UPDATE users SET has_submission = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()

            del user_states[user_id]

            # Google Таблица
            send_to_google_sheets({
                "number": user_data["number"],
                "user_id": user_id,
                "direction": direction,
                "proposal": text,
                "timestamp": now
            })

            send_message(vk, peer_id,
                f"✅ Ваше предложение принято!\n\n"
                f"Номер: {user_data['number']}\n"
                f"Тема: {direction}\n\n"
                f"Предложение:\n{text}\n\n"
                f"Спасибо за участие!",
                keyboard=get_user_keyboard()
            )
            print(f"  Предложение: Номер={user_data['number']}, Тема={direction}")
            return

    # Непонятное сообщение
    conn.close()
    send_message(vk, peer_id, "Используйте кнопки меню:", keyboard=get_user_keyboard())


# ==================== ОСНОВНОЙ ЦИКЛ ====================

def main():
    # Проверка переменных
    if not TOKEN:
        print("ОШИБКА: Не задана переменная VK_TOKEN")
        return

    # Инициализация БД
    print("Инициализация базы данных...")
    init_db()

    try:
        print("Подключение к VK API...")
        vk_session = vk_api.VkApi(token=TOKEN)
        vk = vk_session.get_api()

        try:
            group_info = vk.groups.getById(group_id=GROUP_ID)
            print(f"Подключено к группе: {group_info[0]['name']}")
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка API: {e}")
            return

        print("Подключение к Longpoll...")
        try:
            url = "https://api.vk.com/method/groups.getLongPollServer"
            params = {
                "access_token": TOKEN,
                "group_id": GROUP_ID,
                "v": API_VERSION
            }
            response = requests.get(url, params=params)
            server_info = response.json()["response"]
            key = server_info["key"]
            server = server_info["server"]
            ts = server_info["ts"]
            print("Longpoll подключен")
        except Exception as e:
            print(f"Ошибка Longpoll: {e}")
            return

        print("=" * 50)
        print("БОТ ЗАПУЩЕН!")
        print("=" * 50)
        print("\nКоманды админа:")
        print("  /стат       - статистика")
        print("  /вкл рег    - включить регистрацию")
        print("  /выкл рег   - выключить регистрацию")
        print("  /вкл пред   - включить приём предложений")
        print("  /выкл пред  - выключить приём предложений")
        print("  /рассылка текст  - рассылка всем")
        print("  /роз 5      - розыгрыш призов")
        print("=" * 50)

        while True:
            try:
                url = server
                params = {
                    "act": "a_check",
                    "key": key,
                    "ts": ts,
                    "wait": 25,
                    "mode": 2,
                    "version": 3
                }
                response = requests.get(url, params=params, timeout=30)
                data = response.json()

                if "failed" in data:
                    url_resp = requests.get("https://api.vk.com/method/groups.getLongPollServer", params={
                        "access_token": TOKEN, "group_id": GROUP_ID, "v": API_VERSION
                    })
                    server_info = url_resp.json()["response"]
                    key = server_info["key"]
                    server = server_info["server"]
                    ts = server_info["ts"]
                    continue

                ts = data["ts"]

                for event in data.get("updates", []):
                    if event["type"] == "message_new":
                        message = event["object"]["message"]
                        user_id = message.get("from_id")
                        text = message.get("text", "").strip()
                        peer_id = message["peer_id"]

                        if not text:
                            continue

                        print(f"[{time.strftime('%H:%M:%S')}] Пользователь {user_id}: {text}")
                        handle_message(vk, user_id, peer_id, text)

            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                print(f"Ошибка: {e}")
                time.sleep(5)

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
