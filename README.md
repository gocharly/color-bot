<div align="center">

# Color Bot

Telegram-бот для перекраски векторных анимированных (`.tgs`) и растровых (`.webp`) стикеров и эмодзи.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://github.com/aiogram/aiogram)
[![Pillow](https://img.shields.io/badge/Pillow-11.x-3776AB?style=flat-square)](https://python-pillow.org)
[![TGS Guard](https://img.shields.io/badge/TGS_Guard-≤_63_KB-success?style=flat-square)](https://core.telegram.org/stickers#animated-stickers)

</div>

---

## Как это работает

1. **Отправка**: отправьте боту любой стикер (анимированный `.tgs` или обычный `.webp`), а также кастомные эмодзи из любого сообщения.
2. **Выбор оттенка**: выберите цвет в один клик через инлайн-палитру или введите произвольный HEX-код (например, `#007AFF`).
3. **Результат**: бот мгновенно отправляет готовый результат в чат или добавляет его в персональный стикерпак / эмодзи-пак.

## Архитектура

• **Lottie AST** — перекраска слоёв, контуров и градиентов с поддержкой After Effects 2022+.
• **TGS Guard** — оптимизация JSON и сжатие gzip 9 под лимит Telegram в 63 КБ.
• **WebP LUT** — тоновая перекраска растровых стикеров с сохранением прозрачности.
• **Векторный текст** — замена надписей через перевод шрифта в кривые Безье.
• **Стикерпаки** — создание и пополнение стикерпаков и эмодзи-паков через Bot API.


## Быстрый старт

### Требования
• Python 3.10+  
• Токен бота от [@BotFather](https://t.me/BotFather)

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/gocharly/color-bot.git
cd color-bot

# Создание и активация виртуального окружения
python3 -m venv .venv
source .venv/bin/activate  # Для Linux/macOS
# .venv\Scripts\activate   # Для Windows

# Установка зависимостей
pip install -r requirements.txt
```

### Настройка

Создайте файл `.env` в корне проекта (на основе `.env.example`):
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### Запуск

```bash
python run.py
```

### Тесты

```bash
python -m unittest discover tests
```

---

братец больше интересного в моем тгк: [@charlyex](https://t.me/charlyex)
