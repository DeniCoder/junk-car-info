# Брошенная техника

Народная карта брошенной техники. Интерактивная карта заброшенных автомобилей, тракторов, прицепов и другой техники у дорог.

## Стек

- **Backend**: Python 3.14, Flask 3.1, PostgreSQL 17, SQLAlchemy
- **Frontend**: Leaflet.js, MarkerCluster, vanilla JS
- **Photos**: Pillow (EXIF strip, resize, magic bytes check)
- **PDF**: fpdf2 (админ-панель — экспорт отчётов)

## Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка .env (скопировать из .env.example)
# Создать БД junk_car_info в PostgreSQL

# Инициализация схемы
flask db upgrade

# Заполнить категории и контент
python seed_categories.py
python seed_content.py

# Запуск
flask run --debug
```

## Структура

- `app/` — Flask-приложение
  - `blueprints/api/` — REST API (находки, голосование, геокодинг)
  - `blueprints/web/` — веб-страницы (карта, детальная карточка, контакты)
  - `blueprints/admin/` — админ-панель (дашборд, отчёты, редактор контента)
  - `models/` — SQLAlchemy модели
  - `repositories/` — слой запросов к БД
  - `services/` — бизнес-логика
  - `templates/` — Jinja2 шаблоны
  - `static/` — CSS, JS
- `media/` — загруженные фото (создаётся автоматически)

## Админ-панель

`/admin/login` — токен по умолчанию `admin123`

- **Дашборд** — статистика по находкам и типам техники
- **Отчёты** — таблица с фильтрами, PDF-экспорт, удаление
- **Приватность / Контакты** — редактор контента через Markdown

## Лицензия

MIT
