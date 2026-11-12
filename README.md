# Онлайн-кінотеатр

Курсова робота з дисципліни «Документування програмного забезпечення та шаблони проектування»
(НУ «Львівська Політехніка», варіант 17).

Автор: Мамчур Максим. Репозиторій: https://github.com/Mamchurmax/online-cinema-coursework

## Опис

Вебзастосунок онлайн-кінотеатру:

- каталог фільмів і серіалів (метадані з TMDB) з пошуком і фільтрами: жанр, рік, країна, тип, сортування;
- онлайн-перегляд у різній якості (HLS: 360p / 720p / 1080p), продовження з місця зупинки;
- реєстрація, вхід (JWT) і профілі користувачів; історія переглядів, «Вибране», сповіщення;
- підписки **Free** (до 720p, pre-roll реклама) і **Premium** (до 1080p, без реклами); mock-оплата;
- рекомендації на основі історії переглядів (три алгоритми);
- адмін-панель: тайтли, сезони, епізоди, відео, реклама, тарифи, користувачі, платежі, **звіти з графіками**:
  популярні фільми та жанри, активність користувачів, дохід від підписок.

## Стек

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 17, JWT
- **Frontend:** React, Vite, TypeScript, React Router, TanStack Query, hls.js, Recharts
- **Інфраструктура:** Docker Compose (db, backend, frontend на nginx), ffmpeg
- **Документація:** PlantUML (`docs/uml/`, PNG у `docs/uml/png/`)

## Швидкий старт з нуля

Потрібен [Docker Desktop](https://www.docker.com/products/docker-desktop/). Усі команди виконуються з кореня репозиторію.

1. **Налаштування.** Скопіюйте приклад і заповніть щонайменше `JWT_SECRET_KEY`, `ADMIN_PASSWORD` (від 8 символів) і,
   для імпорту каталогу, `TMDB_API_TOKEN` (див. [змінні оточення](#змінні-оточення)):

   ```bash
   cp .env.example .env
   ```

2. **Запуск стеку.** Під час старту backend сам застосовує міграції (`alembic upgrade head`):

   ```bash
   docker compose up -d --build
   ```

3. **Тарифи й адміністратор** (повторний запуск безпечний):

   ```bash
   docker compose exec backend python -m scripts.seed
   ```

4. **Каталог з TMDB** — [детальніше](#імпорт-каталогу-з-tmdb):

   ```bash
   docker compose exec backend python -m scripts.import_tmdb
   ```

5. **Відео (необов'язково, але без нього плеєр не працює)** — завантажити фільми Blender, перекодувати в HLS
   і прив'язати до тайтлів, див. [Демо-відео](#демо-відео-hls).

6. Відкрийте **http://localhost:3000**, увійдіть як `ADMIN_EMAIL` / `ADMIN_PASSWORD` — у меню з'явиться «Адмінка».

Адреси:

- **Вебзастосунок: http://localhost:3000** (адмін-панель — http://localhost:3000/admin)
- API: http://localhost:8000/api/v1/health
- Swagger UI (усі ендпоінти REST API): http://localhost:8000/docs
- PostgreSQL: `localhost:5432` (користувач, пароль і база — з `.env`)

Корисні команди:

```bash
docker compose logs -f backend   # логи backend
docker compose ps                # стан контейнерів
docker compose down              # зупинити (дані БД зберігаються у volume pgdata)
docker compose down -v           # зупинити й видалити дані БД
```

База створюється з українською ICU-колацією (`uk-UA`), тому сортування за назвою відповідає українському алфавіту.
Якщо volume `pgdata` був створений до цієї зміни, пересоздайте його: `docker compose down -v`, `docker compose up -d`,
а потім повторіть кроки 3–5.

### Змінні оточення

| Змінна | Призначення |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | облікові дані PostgreSQL у Docker |
| `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` | порти на хості (5432 / 8000 / 3000) |
| `DATABASE_URL` | лише для запуску backend поза Docker; у Compose задається автоматично |
| `CORS_ORIGINS` | дозволені джерела для dev-сервера Vite |
| `JWT_SECRET_KEY` | секрет підпису токенів: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | час життя токена (за замовчуванням 60 хв) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | адміністратор, якого створює `scripts.seed` |
| `TMDB_API_TOKEN` | API Read Access Token TMDB для імпорту каталогу |

> Після зміни `.env` контейнер треба **пересоздати**, а не просто перезапустити — інакше він не побачить нових значень:
> `docker compose up -d --force-recreate backend`.

### Тарифи й адміністратор

`scripts.seed` створює тарифи **Free** (0 грн, до 720p, з рекламою) і **Premium** (до 1080p, без реклами) та
адміністратора з `ADMIN_EMAIL` / `ADMIN_PASSWORD`. Без пароля адміністратор не створюється. Інший email:

```bash
docker compose exec backend python -m scripts.seed --admin-email boss@example.com
```

Ціни, період і якість тарифів потім змінюються в адмінці («Тарифи»). Зробити адміністратором наявного користувача
можна там само, у розділі «Користувачі».

### Імпорт каталогу з TMDB

1. Отримайте **API Read Access Token** на https://www.themoviedb.org/settings/api (потрібен безкоштовний акаунт TMDB).
2. Впишіть його в `.env`: `TMDB_API_TOKEN=...` і пересоздайте backend: `docker compose up -d --force-recreate backend`.
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
Окремі тайтли можна імпортувати й з адмінки («Тайтли» → «Імпорт з TMDB»).

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
Інші перекодовані папки з `media/hls` можна прив'язати до фільмів чи епізодів в адмінці («Відео» / сторінка тайтлу).

## Як користуватися

### Глядач

- **Каталог** — пошук за назвою, фільтри (жанр, рік, країна, фільм/серіал), сортування; на головній — рядок рекомендацій
  з вкладками «Для вас» / «За жанрами» / «Популярне».
- **Сторінка тайтлу** — опис, жанри, сезони й епізоди, кнопки «Дивитися» і «У вибране».
- **Плеєр** (`/watch/:id`) — меню якості (недоступні на тарифі позначені 🔒), pre-roll реклама на Free, прогрес
  зберігається кожні 10 с, «Продовжити перегляд» на головній, історія — `/history`.
- **Тарифи й оплата** (`/plans` → `/checkout`) — оплата імітується: на сторінці оплати оберіть сценарій
  `success` (одразу успішно), `pending` (очікує відповіді банку — кнопка «Симулювати відповідь банку» або рішення
  адміністратора) чи `failed`. Після успішної оплати підписка активується, приходить сповіщення (дзвіночок).

### Адміністратор (`/admin`)

| Розділ | Що можна робити |
|---|---|
| Тайтли | створення, редагування, видалення; імпорт з TMDB; сезони й епізоди; прив'язка відео |
| Відео | прив'язані відео й вільні папки `media/hls` |
| Платежі | платежі в стані `pending`: підтвердити або відхилити |
| Тарифи | назва, ціна, період, максимальна якість, реклама |
| Користувачі | пошук, зміна ролі, видалення (користувача з платежами видалити не можна) |
| Реклама | ролики pre-roll і їх активність |
| **Звіти** | популярні фільми та жанри, активність користувачів, дохід від підписок за період |

Звіти будуються за обраний період (7 / 30 / 90 днів, рік або довільні дати, до 366 днів; дні за UTC; періоди
довші за 92 дні групуються по місяцях). Кожен звіт містить ключові показники, графіки (Recharts) і таблицю, яку
можна завантажити як CSV. Той самий JSON віддає API: `GET /api/v1/admin/reports/{popularity|activity|revenue}?date_from=2026-11-01&date_to=2026-11-30`.

### Щоденне завдання підписок

Нагадування за 3 дні та 1 день до кінця підписки і закриття прострочених підписок:

```bash
docker compose exec backend python -m scripts.check_subscriptions
```

Запускайте раз на день (cron / Планувальник завдань Windows).

## Архітектура

Шари backend: **router** (`app/api/v1`) → **service** (`app/services`, уся бізнес-логіка) → **repository**
(`app/repositories`, запити SQLAlchemy) → **model** (`app/models`). Схеми запитів і відповідей — Pydantic (`app/schemas`).

### GoF-патерни

| Патерн | Де | Роль |
|---|---|---|
| Singleton | `core/config.py` — `Settings` | єдина конфігурація застосунку |
| Builder | `services/catalog/query_builder.py` — `CatalogQueryBuilder` | покроково будує запит каталогу з фільтрів |
| Adapter | `services/importers/tmdb_adapter.py` — `TmdbAdapter` | відповіді TMDB → доменні дані (`CatalogSource`) |
| Strategy | `services/streaming/policies.py` — `FreePolicy`, `PremiumPolicy` | тарифні політики: реклама, максимальна якість |
| Proxy | `services/streaming/access_proxy.py` — `StreamAccessProxy` | віддає master-плейлист лише з дозволеними якостями |
| Observer | `services/events/` — `EventBus` + слухачі | `TitleWatched`, `PaymentSucceeded`, `SubscriptionExpiring` → статистика, підписка, сповіщення |
| Factory Method | `services/payments/factory.py` — `PaymentProviderFactory` | створює платіжного провайдера (mock) |
| State | `services/payments/states.py` — `PendingState`, `SucceededState`, `FailedState` | переходи статусу платежу |
| Strategy | `services/recommendations/strategies.py` — `GenreBasedStrategy`, `PopularityStrategy`, `HybridStrategy` | алгоритми рекомендацій |
| Template Method | `services/reports/base.py` — `BaseReport` → `PopularityReport`, `ActivityReport`, `RevenueReport` | `build()` = collect → aggregate → format |

Як вони працюють разом: Builder знаходить фільм → Proxy з тарифною Strategy видає потік → Observer фіксує перегляд →
Recommendation Strategy використовує історію → Template Method будує звіт. Окремо: Factory створює провайдера →
State веде платіж → Observer активує підписку.

### Діаграми (`docs/uml/`)

| Файл | Зміст |
|---|---|
| `use-case.puml` | варіанти використання (клієнт і адміністратор) |
| `class.puml` | діаграма класів, патерни виділені кольорами (легенда праворуч угорі) |
| `er.puml` | схема бази даних |
| `sequence-playback.puml`, `sequence-payment.puml` | перегляд відео й оплата підписки |

PNG генеруються PlantUML (потрібна Java):

```bash
java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar -tpng -o png docs/uml/*.puml
```

### Структура репозиторію

```
backend/
  app/
    api/v1/        REST API (auth, catalog, playback, billing, recommendations, admin, reports)
    core/          конфігурація (Singleton), БД, безпека (JWT, хеш паролів)
    models/        моделі SQLAlchemy
    schemas/       схеми Pydantic
    repositories/  доступ до даних
    services/      бізнес-логіка й патерни
  alembic/         міграції
  scripts/         seed, import_tmdb, register_videos, check_subscriptions, transcode.sh, make_ad.sh
  tests/           pytest
frontend/src/      api/ components/ pages/ hooks/ admin/ (адмінка — окремий lazy-чанк)
media/             вихідні відео й HLS (не в git)
docs/uml/          діаграми PlantUML
```

## Розробка

### Backend локально

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

### Тести

Тести використовують SQLite у пам'яті, не потребують PostgreSQL і не читають `.env` (162 тести):

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

### Frontend локально

Потрібен Node.js 22 LTS або новіший. Backend має працювати на `localhost:8000` (локально або через `docker compose up -d backend`).

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, запити /api проксуються на backend
npm run build        # перевірка типів і production-збірка
```

## Типові проблеми

| Симптом | Рішення |
|---|---|
| `docker: command not found` у терміналі Windows | додайте до PATH `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin` або запустіть Docker Desktop |
| backend не бачить нового значення з `.env` | `docker compose up -d --force-recreate backend` |
| імпорт TMDB пише, що токена немає | перевірте `TMDB_API_TOKEN` у `.env` і пересоздайте backend |
| плеєр каже, що відео немає | перекодуйте відео й запустіть `scripts.register_videos` (або прив'яжіть в адмінці) |
| немає пункту «Адмінка» | увійдіть як адміністратор; створіть його через `scripts.seed` з `ADMIN_PASSWORD` |
| забули пароль адміністратора | змініть `ADMIN_PASSWORD` у `.env`, пересоздайте backend і запустіть `scripts.seed` ще раз |
| неправильне сортування кирилиці | volume БД створено до ICU-колації: `docker compose down -v` і кроки швидкого старту заново |

## Відомі обмеження

- iOS Safari не відтворює відео (hls.js потребує Media Source Extensions); у настільних браузерах і на Android усе працює.
- Сегменти й варіантні плейлисти в `/media/hls` — статичні файли; Proxy захищає master-плейлист, через який плеєр їх знаходить.
- Оплата імітується (mock-провайдер); реальний платіжний шлюз підключається новою фабрикою (Factory Method).
- Історія переглядів зберігає останню позицію в кожному відео, тому звіт активності рахує день останнього перегляду.
