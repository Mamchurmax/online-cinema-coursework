# Онлайн-кінотеатр

Курсова робота з дисципліни «Документування програмного забезпечення та шаблони проектування»
(НУ «Львівська політехніка», варіант 17).

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

Повну інструкцію запуску через Docker Compose буде додано пізніше.

### Backend локально (для розробки)

Потрібен Python 3.12.

```bash
cp .env.example .env
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows (Git Bash); у Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- Тести: `pytest`

## Статус

Проєкт у розробці.
