# Брошенная техника — проект для нейросетей

## Описание

Народная карта брошенной техники. Пользователи анонимно отмечают на карте заброшенные автомобили, тракторы, прицепы и другую технику. Фото загружаются, EXIF-данные удаляются.

## Технологии

- Python 3.14, Flask 3.1.1, PostgreSQL 17
- SQLAlchemy + Flask-Migrate, psycopg3
- Leaflet.js 1.9 + MarkerCluster, Nominatim (геокодинг)
- Pillow (обработка фото), fpdf2 (PDF-отчёты)
- Flask-Limiter, Flask-Talisman

## Архитектура

**Шаблон**: Blueprint + Repository + Service

```
app/
  blueprints/       # Маршруты (api, web, admin)
  models/           # SQLAlchemy модели
  repositories/     # Запросы к БД
  services/         # Бизнес-логика
  templates/        # Jinja2
  static/           # CSS, JS
```

## База данных

**Подключение**: `postgresql+psycopg://postgres:147258As$@localhost:5432/junk_car_info`
**ORM**: Flask-SQLAlchemy 3.1 (`from app.extensions import db`)
**Миграции**: Flask-Migrate (`flask db migrate`, `flask db upgrade`)

### Таблицы

- `findings` — находки (id uuid, category_id FK, lat/lon Numeric(9,6), status, creator_fingerprint, reports_count)
- `categories` — типы техники (id SERIAL, title, slug, parent_id nullable — иерархия)
- `finding_photos` — фото (id SERIAL, finding_id FK, file_path, thumb_path, web_url, thumb_url, sort_order)
- `votes` — голоса (id SERIAL, finding_id FK CASCADE, fingerprint, vote_type, created_at)
- `reports` — жалобы (id SERIAL, finding_id FK CASCADE, reason, created_at)
- `site_content` — редактируемые страницы (slug PK, title, content_md, updated_at)

## API endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/api/findings?bbox=...` | Список находок в bounds |
| GET | `/api/findings/<id>` | Детально |
| POST | `/api/findings/` | Создать (multipart) |
| POST | `/api/findings/<id>/vote` | Голосовать |
| POST | `/api/findings/<id>/report` | Пожаловаться |
| GET | `/api/geocode?q=...` | Геокодинг (прокси к Nominatim) |
| GET | `/api/categories` | Типы техники |

## Жизненный цикл находки

1. Пользователь заполняет форму (фото, описание, адрес — обязательны)
2. Находка создаётся со статусом `published` сразу (модерации нет)
3. Любой может проголосовать "НА МЕСТЕ" (confirmed) или "УВЕЗЛИ" (removed)
4. При 3 голосах "УВЕЗЛИ" → статус становится `hidden`
5. `confirmed_count_others` — количество подтверждений от чужих пользователей (без учёта автора)

## Дизайн

**Промышленная тёмная тема**:
- Фон: `#16120F`, акценты: `#C0532A` (ржавый), `#E3B53E` (жёлтый), `#6F7A52` (мох)
- Шрифты: Archivo Condensed (заголовки), JetBrains Mono (метаданные), IBM Plex Sans (текст)
- `z-index`: карта 0, grain 1, хедер/легенда 1000, футер 1100, лайтбокс 2000
- Футер фиксированный снизу: контакты | политика конфиденциальности
- Зернистая текстура: `body::after` с `z-index: 1`, полупрозрачный PNG

## Важные правила

1. **Фото хранятся на диске** в `media/`, не в БД. Пути сохраняются в PostgreSQL.
2. **Личных данных нет** — нет аккаунтов, EXIF удаляется, IP только для rate-limit.
3. **Blueprint pattern**: `__init__.py` определяет blueprint, `views.py` импортирует из `__init__.py`.
4. **Конфиг** читается через `current_app.config` внутри request context, иначе через `app.config`.
5. **Файлы seed** запускать отдельно: `python seed_categories.py`, `python seed_content.py`.
6. **Админ** — `/admin/login`, токен `admin123` (из `ADMIN_TOKEN` в `.env`).
7. **Markdown** для контента страниц (приватность, контакты) — парсится inline в шаблоне.
8. **Никаких комментариев в коде** — чистый код без пояснений.
9. **ES5 JavaScript** без транспиляции — никаких import/export, const/let/стрелок.
10. **Шаблоны Jinja2** — минимальная логика, всё тяжёлое в Python.

## Частые задачи

### Добавить маршрут
1. Создать/дополнить `views.py` в нужном blueprint
2. Если нужна новая модель — создать в `app/models/`
3. Если нужна бизнес-логика — добавить в `app/services/`
4. Если нужен новый запрос — добавить в `app/repositories/`

### Добавить поле в таблицу
1. Добавить колонку в модель
2. `flask db migrate -m "описание"`
3. `flask db upgrade`

### Исправить шаблон
Все шаблоны в `app/templates/`. CSS в `app/static/css/main.css`. JS в `app/static/js/`.

### Запуск тестов
Тестов нет. Проверка: `flask run --debug` и ручное тестирование в браузере.

## Команды

```bash
pip install -r requirements.txt
flask db upgrade
python seed_categories.py
python seed_content.py
flask run --debug
```
