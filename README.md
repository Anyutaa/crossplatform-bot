# Booking System — Telegram Bot

Telegram-бот для системы бронирования жилья. Альтернативный клиент к [Booking System API](https://github.com/Anyutaa/Crossplatform_web_api): пользователь регистрируется, авторизуется и создаёт бронирования прямо в Telegram, не открывая веб-сайт.

---

## Стек

- **Python 3.12**
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) — фреймворк для Telegram-ботов
- [requests](https://docs.python-requests.org/) — HTTP-клиент к backend API
- Хранение состояний пользователей через словари в памяти (отдельные словари для каждого этапа диалога: регистрация, логин, добавление комнаты, бронирование)
- JWT-токен сохраняется в памяти на время сессии и используется в заголовке `Authorization: Bearer ...` для всех защищённых запросов

---

## Архитектура взаимодействия

```
┌─────────┐         ┌──────────┐          ┌──────────────┐
│  User   │ ──────► │ Telegram │ ──────► │     Bot      │
│         │         │   API    │          │  (this repo) │
└─────────┘         └──────────┘          └──────┬───────┘
                                                  │ HTTP + JWT
                                                  ▼
                                          ┌──────────────┐
                                          │ Booking API  │
                                          │  (ASP.NET)   │
                                          └──────┬───────┘
                                                  │ EF Core
                                                  ▼
                                          ┌──────────────┐
                                          │   SQLite     │
                                          └──────────────┘
```

Бот не имеет собственной БД — все данные хранятся в backend API. Это позволяет одному и тому же пользователю работать **из веб-интерфейса** (`crossplatform-front`) и **из Telegram-бота** одновременно — состояние согласовано через общий backend.

---

## Запуск

### Требования
- Python 3.10+
- Запущенный [Booking System API](https://github.com/Anyutaa/Crossplatform_web_api) на `http://localhost:5000`
- Telegram Bot API token от [@BotFather](https://t.me/BotFather)

### Установка

```bash
git clone https://github.com/Anyutaa/crossplatform-bot.git
cd crossplatform-bot

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### Настройка

Скопируйте шаблон секретов и впишите свой токен бота:

```bash
cp secrets.example.py secrets.py
```

Откройте `secrets.py` и замените `"your_telegram_bot_token_here"` на реальный токен, полученный у @BotFather.

> ⚠️ Файл `secrets.py` уже добавлен в `.gitignore` и **никогда не должен** попадать в репозиторий.

### Запуск

```bash
python main.py
```

Бот запускается в режиме long polling и ждёт сообщений.

---

## Сценарий использования

1. Пользователь пишет боту `/start`
2. Бот проверяет в API, есть ли уже аккаунт с этим `TelegramId`:
   - **Аккаунт найден** → запрос пароля → логин → главное меню
   - **Аккаунта нет** → пошаговая регистрация (email → имя → пароль) → автоматический логин → главное меню
3. После авторизации главное меню предлагает 4 действия:
   - Посмотреть комнаты
   - Добавить комнату
   - Забронировать комнату
   - Мои бронирования

---

## Связанные репозитории

| Компонент       | Репозиторий                                                                  |
|-----------------|------------------------------------------------------------------------------|
| Backend API     | [Crossplatform_web_api](https://github.com/Anyutaa/Crossplatform_web_api)    |
| Web frontend    | [crossplatform-front](https://github.com/Anyutaa/crossplatform-front)        |
| Telegram bot    | _текущий репозиторий_                                                        |

---

## Возможные улучшения

- Вынести URL backend API в `secrets.py` или переменную окружения вместо хардкода `http://localhost:5000`
- Заменить in-memory хранилище состояний на Redis (текущая реализация теряет состояние при перезапуске бота и не масштабируется на несколько процессов)
- Добавить inline-клавиатуры с кнопками вместо ReplyKeyboard для более удобного UX
- Уведомления пользователю при подтверждении/отмене брони со стороны администратора (через webhook от backend)
- Контейнеризация (`Dockerfile` + `docker-compose` совместно с backend)

---

## Лицензия

MIT
