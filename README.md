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
docker compose exec backend python -m scripts.import_tmdb --anime-movies 1 --anime-series 2 --no-demo   # популярне японське аніме
```

Повторний імпорт безпечний: наявні тайтли оновлюються за `tmdb_id`, дублікати не створюються.
Метадані завантажуються українською, а якщо перекладу немає — англійською (назви, описи, назви епізодів).
Ток-шоу, мильні опери, новини й реаліті-шоу пропускаються; для довгих серіалів зберігається до 100 епізодів на сезон (`--max-episodes`).

### Демо-відео (HLS)

Для перегляду використовуються відкриті фільми Blender Foundation (ліцензія CC BY):
Big Buck Bunny, Sintel, Tears of Steel, Elephants Dream. Відео не зберігаються в git: їх
треба завантажити й перекодувати один раз (~2,7 ГБ, конвертація займає 20–40 хв).

1. Завантажте файли в `media/source/` з https://download.blender.org:
   - `peach/bigbuckbunny_movies/big_buck_bunny_1080p_h264.mov.zip` (розпакуйте)
   - `durian/movies/Sintel.2010.1080p.mkv`
   - `demo/movies/ToS/tears_of_steel_1080p.mov.zip` (розпакуйте)
   - `ED/elephantsdream-1024-h264-st-aac.mov`
2. Перекодуйте в HLS (ffmpeg уже є в образі backend):

```bash
docker compose run --rm backend bash scripts/transcode.sh /media/source/big_buck_bunny_1080p_h264.mov /media/hls/big-buck-bunny
docker compose run --rm backend bash scripts/transcode.sh /media/source/Sintel.2010.1080p.mkv /media/hls/sintel
docker compose run --rm backend bash scripts/transcode.sh /media/source/tears_of_steel_1080p.mov /media/hls/tears-of-steel
docker compose run --rm backend bash scripts/transcode.sh /media/source/elephantsdream-1024-h264-st-aac.mov /media/hls/elephants-dream
docker compose run --rm backend bash scripts/make_ad.sh /media/hls/ads/demo
```

3. Прив'яжіть відео до тайтлів (після імпорту каталогу з TMDB):

```bash
docker compose exec backend python -m scripts.register_videos
```

`transcode.sh` робить якості 360p / 720p / 1080p (лише ті, що не перевищують оригінал) і
master-плейлист `master.m3u8`; `make_ad.sh` генерує 10-секундний рекламний ролик.

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
