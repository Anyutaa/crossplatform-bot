import telebot
from secrets import secrets
from telebot import types
import requests
import logging
import time

telebot.logger.setLevel(logging.DEBUG)

API = "http://localhost:5000/api"
bot_token = secrets.get('BOT_API_TOKEN')
bot = telebot.TeleBot(bot_token)

# состояния
auth_users = {}        # chat_id -> {token, user_id}
register_states = {}   # chat_id -> регистрация
login_states = {}      # chat_id -> вход
add_room_states = {}
booking_states = {}

# START 

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    tg_id = message.from_user.id
    tg_username = message.from_user.username

    r = requests.get(f"{API}/auth/telegram/{tg_id}")

    if r.status_code == 200:
        data = r.json()
        user = data["user"]

        login_states[chat_id] = {
            "telegramId": tg_id,
            "email": user["email"]
        }

        bot.send_message(chat_id, "Аккаунт найден. Введите пароль:")
    else:
        register_states[chat_id] = {
            "step": "email",
            "telegramId": tg_id,
            "telegramUsername": tg_username
        }
        bot.send_message(chat_id, "Аккаунт не найден.\nВведите Email для регистрации:")

# LOGIN 

@bot.message_handler(func=lambda m: m.chat.id in login_states)
def handle_login(message):
    chat_id = message.chat.id
    password = message.text.strip()
    state = login_states[chat_id]

    # 1. логин по email + password
    r = requests.post(f"{API}/auth/login", json={
        "Email": state["email"],
        "Password": password
    })

    if r.status_code != 200:
        bot.send_message(chat_id, "Неверный пароль. Попробуйте ещё раз:")
        return

    token = r.json()["token"]

    # 2. получаем пользователя по telegramId
    r2 = requests.get(f"{API}/auth/telegram/{state['telegramId']}")
    data = r2.json()
    user = data["user"]

    auth_users[chat_id] = {
        "token": token,
        "user_id": user["id"]
    }

    del login_states[chat_id]

    bot.send_message(chat_id, f"Вы вошли как {user['name']}")
    send_main_menu(chat_id)


# REGISTRATION 

@bot.message_handler(func=lambda m: m.chat.id in register_states)
def handle_registration(message):
    chat_id = message.chat.id
    state = register_states[chat_id]

    if state["step"] == "email":
        state["email"] = message.text
        state["step"] = "name"
        bot.send_message(chat_id, "Введите имя:")

    elif state["step"] == "name":
        state["name"] = message.text
        state["step"] = "password"
        bot.send_message(chat_id, "Введите пароль (не менее 6 символов):")

    elif state["step"] == "password":
        password = message.text.strip()

        if len(password) < 6:
            bot.send_message(chat_id, "Пароль слишком короткий. Попробуйте снова:")
            return

        payload = {
            "Email": state["email"],
            "Name": state["name"],
            "Password": password,
            "TelegramId": state["telegramId"],
            "TelegramUsername": state["telegramUsername"]
        }

        r = requests.post(f"{API}/auth/register", json=payload)

        if r.status_code != 200:
            bot.send_message(chat_id, "Ошибка регистрации")
            return

        data = r.json()
        user = data["user"]
        token = data["token"]

        auth_users[chat_id] = {
            "token": token,
            "user_id": user["id"]
        }

        del register_states[chat_id]

        bot.send_message(chat_id, f"Регистрация завершена. Добро пожаловать, {user['name']}")
        send_main_menu(chat_id)

# MENU 

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        "Посмотреть комнаты",
        "Добавить комнату",
        "Забронировать комнату",
        "Мои бронирования"
    )
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda m:
    m.chat.id not in register_states
    and m.chat.id not in login_states
    and m.chat.id not in add_room_states
    and m.chat.id not in booking_states
)
def handle_buttons(message):
    chat_id = message.chat.id
    text = message.text

    if text == "Посмотреть комнаты":
        show_rooms(chat_id)

    elif text == "Добавить комнату":
        add_room_states[chat_id] = {"step": "name"}
        bot.send_message(chat_id, "Введите название комнаты:")

    elif text == "Забронировать комнату":
        start_booking(chat_id)

    elif text == "Мои бронирования":
        show_my_bookings(chat_id)

# ROOMS

def show_rooms(chat_id):
    if chat_id not in auth_users:
        bot.send_message(chat_id, "Вы не авторизованы")
        return

    token = auth_users[chat_id]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API}/rooms", headers=headers)
    rooms = r.json() if r.status_code == 200 else []

    if not rooms:
        bot.send_message(chat_id, "Комнат нет")
        return

    text = "Ваши комнаты:\n\n"
    for room in rooms:
        text += f"{room['name']} — {room['pricePerDay']} руб/день\n"

    bot.send_message(chat_id, text)

@bot.message_handler(func=lambda m: m.chat.id in add_room_states)
def handle_add_room(message):
    chat_id = message.chat.id
    state = add_room_states[chat_id]

    if state["step"] == "name":
        state["name"] = message.text
        state["step"] = "price"
        bot.send_message(chat_id, "Введите цену за день:")

    elif state["step"] == "price":
        try:
            price = float(message.text.replace(",", "."))
        except ValueError:
            bot.send_message(chat_id, "Введите число")
            return

        token = auth_users[chat_id]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": state["name"],
            "pricePerDay": price
        }

        r = requests.post(f"{API}/rooms", json=payload, headers=headers)

        if r.status_code in (200, 201):
            bot.send_message(chat_id, "Комната добавлена")
        else:
            bot.send_message(chat_id, "Ошибка добавления")

        del add_room_states[chat_id]
        send_main_menu(chat_id)

# BOOKING 

def start_booking(chat_id):
    r = requests.get(f"{API}/rooms/available")
    rooms = r.json() if r.status_code == 200 else []

    if not rooms:
        bot.send_message(chat_id, "Нет доступных комнат")
        return

    booking_states[chat_id] = {
        "step": "choose_room",
        "rooms": rooms
    }

    msg = "Доступные комнаты:\n"
    for i, room in enumerate(rooms, start=1):
        msg += f"{i}. {room['name']} — {room['pricePerDay']} ₽/день\n"

    msg += "\nВведите номер комнаты, которую хотите забронировать:"

    send_long_message(chat_id, msg)



@bot.message_handler(func=lambda m: m.chat.id in booking_states)
def handle_booking(message):
    chat_id = message.chat.id
    state = booking_states[chat_id]

    if state["step"] == "choose_room":
        try:
            index = int(message.text) - 1
            state["room"] = state["rooms"][index]
        except:
            bot.send_message(chat_id, "Неверный номер")
            return

        state["step"] = "start"
        bot.send_message(chat_id, "Введите дату начала (YYYY-MM-DD):")

    elif state["step"] == "start":
        state["start"] = message.text
        state["step"] = "end"
        bot.send_message(chat_id, "Введите дату окончания (YYYY-MM-DD):")

    elif state["step"] == "end":
        token = auth_users[chat_id]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "roomIds": str(state["room"]["id"]),
            "start": state["start"],
            "end": message.text
        }

        r = requests.post(f"{API}/bookings", params=params, headers=headers)

        bot.send_message(chat_id,
            "Бронирование создано" if r.status_code in (200, 201)
            else "Ошибка бронирования"
        )

        del booking_states[chat_id]
        send_main_menu(chat_id)

# MY BOOKINGS 
def send_long_message(chat_id, text):
    MAX_LEN = 3500
    for i in range(0, len(text), MAX_LEN):
        try:
            bot.send_message(chat_id, text[i:i + MAX_LEN])
            time.sleep(0.3)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Ошибка соединения при отправке сообщения: {e}")
            time.sleep(1) 

def show_my_bookings(chat_id):
    token = auth_users[chat_id]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API}/bookings", headers=headers)
    bookings = r.json() if r.status_code == 200 else []

    if not bookings:
        bot.send_message(chat_id, "Бронирований нет")
        return

    text = "Ваши бронирования:\n\n"

    for b in bookings:
        rooms = b.get("rooms", [])
        names = ", ".join(r["roomName"] for r in rooms)

        text += (
            f"Комнаты: {names}\n"
            f"Даты: {b['startDate']} → {b['endDate']}\n\n"
        )

    bot.send_message(chat_id, text)


bot.polling(none_stop=True)
