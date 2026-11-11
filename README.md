# Онлайн-кінотеатр

Курсова робота з дисципліни «Документування програмного забезпечення та шаблони проектування»
(НУ «Львівська Політехніка», варіант 17).

Автор: Мамчур Максим.

## Опис

Вебзастосунок онлайн-кінотеатру:

- каталог фільмів і серіалів з пошуком і фільтрами (жанр, рік, країна);
- онлайн-перегляд у різній якості (HLS: 360p / 720p / 1080p);
- реєстрація та профілі користувачів;
- підписки Free (з рекламою) та Premium (без реклами);
- рекомендації на основі історії переглядів, «Вибране»;
- адмін-панель і звіти: популярні фільми та жанри, активність користувачів, дохід від підписок.

## Стек

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, JWT
- **Frontend:** React, Vite, TypeScript, TanStack Query, hls.js, Recharts
- **Інфраструктура:** Docker Compose, ffmpeg
- **Документація:** PlantUML (`docs/uml/`)

## Запуск

### Через Docker Compose (рекомендовано)

Потрібен [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env          # за потреби змініть паролі, порти та JWT_SECRET_KEY
docker compose up -d --build
```

Під час старту backend автоматично застосовує міграції бази даних (`alembic upgrade head`).

- **Вебзастосунок: http://localhost:3000**
- API: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- PostgreSQL: `localhost:5432` (користувач, пароль і база — з `.env`)

Корисні команди:

```bash
docker compose logs -f backend   # логи backend
docker compose down              # зупинити (дані БД зберігаються у volume pgdata)
docker compose down -v           # зупинити й видалити дані БД
```

База створюється з українською ICU-колацією (`uk-UA`), тому сортування за назвою відповідає українському алфавіту.
Якщо volume `pgdata` був створений до цієї зміни, пересоздайте його: `docker compose down -v`, `docker compose up -d`, а потім повторіть імпорт каталогу.

### Імпорт каталогу з TMDB

1. Отримайте **API Read Access Token** на https://www.themoviedb.org/settings/api (потрібен безкоштовний акаунт TMDB).
2. Впишіть його в `.env`: `TMDB_API_TOKEN=...`, після чого перезапустіть backend: `docker compose up -d backend`.
3. Запустіть імпорт:

```bash
docker compose exec backend python -m scripts.import_tmdb                  # демо-фільми Blender + по 1 сторінці популярних фільмів і серіалів
docker compose exec backend python -m scripts.import_tmdb --movies 603 680 # конкретні фільми за TMDB id
docker compose exec backend python -m scripts.import_tmdb --series 1399 --max-seasons 1
docker compose exec backend python -m scripts.import_tmdb --popular-movies 3 --popular-series 2
```

Повторний імпорт безпечний: наявні тайтли оновлюються за `tmdb_id`, дублікати не створюються.
Метадані завантажуються українською, а якщо перекладу немає — англійською.

### Backend локально (для розробки)

Потрібен Python 3.12. База даних — з Docker Compose:

```bash
cp .env.example .env
docker compose up -d db
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows (Git Bash); у Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Тести використовують SQLite у пам'яті й не потребують PostgreSQL: `pytest`.

### Frontend локально (для розробки)

Потрібен Node.js 22 LTS. Backend має працювати на `localhost:8000` (локально або через `docker compose up -d backend`).

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, запити /api проксуються на backend
npm run build        # перевірка типів і production-збірка
```

## Статус

Проєкт у розробці.
