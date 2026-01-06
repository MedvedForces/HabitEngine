# HabitEngine

HabitEngine — аналитический бэкенд для трекинга привычек с гибкими расписаниями, IANA-таймзонами и расчётами стриков, heatmap и сводной статистики на стороне PostgreSQL.

## Возможности

- Регистрация и JWT-аутентификация через OAuth2 Bearer.
- Профиль пользователя с IANA-таймзоной.
- Бинарные и количественные привычки.
- Расписания `daily`, `weekdays` и `weekly_quota`.
- Архивация привычек без потери истории.
- Несколько количественных чек-инов за один локальный день.
- Заморозки пропущенных дней.
- Cursor-пагинация истории чек-инов без `OFFSET`.
- Стрики в днях или неделях.
- GitHub-подобный heatmap и completion rate за 7 и 30 дней.
- PostgreSQL-аналитика вместо загрузки всей истории в Python.

## Стек

- Python 3.12+
- FastAPI и Pydantic v2
- PostgreSQL 16
- SQLAlchemy 2.0 async и asyncpg
- Alembic
- PyJWT и argon2-cffi
- pytest, pytest-asyncio и HTTPX
- Ruff
- uv
- Docker и Docker Compose

## Архитектура

```text
api -> services -> repositories -> models
```

- `app/api`: роутеры, Pydantic-схемы, Depends и exception handlers.
- `app/services`: бизнес-правила и валидация итогового состояния.
- `app/repositories`: SQLAlchemy CRUD и PostgreSQL-аналитические запросы.
- `app/models`: SQLAlchemy-модели и ограничения базы.
- `app/core`: settings, security и доменные исключения.
- `migrations`: миграции Alembic.
- `tests`: интеграционные тесты FastAPI и PostgreSQL.

## Архитектурные решения

Чек-ин хранит `logged_at` как UTC `TIMESTAMPTZ` и отдельно `local_date` как `DATE`. Первое поле сохраняет точное время события, второе фиксирует локальную дату на момент записи. Поэтому последующее изменение таймзоны пользователя не меняет прошлую историю.

Бинарный чек-ин защищён в сервисе внутри транзакции с блокировкой строки привычки `SELECT ... FOR UPDATE`. Блокировка предотвращает одновременное создание двух чек-инов на одну локальную дату и гарантирует проверку архивации под актуальным состоянием строки.

Стрики и сводная аналитика рассчитываются PostgreSQL через CTE, агрегаты и оконные функции, включая gaps-and-islands. Полные данные не выгружаются в Python. Для реальных строк с чек-инами и заморозками используется `FULL OUTER JOIN`; пустые дни не генерируются в стриковых запросах.

Индекс `(user_id, is_archived, created_at)` ускоряет выборки привычек конкретного пользователя с фильтром архивации и сортировкой. Индекс `(habit_id, local_date DESC, id DESC)` закрывает агрегацию истории по датам и keyset-пагинацию с кортежным сравнением `(local_date, id)`, где `OFFSET` не используется.

## Быстрый старт

Скопировать пример конфигурации:

```bash
copy .env.example .env
```

Запустить приложение и PostgreSQL:

```bash
docker compose up --build
```

Применить миграции:

```bash
docker compose exec app uv run alembic upgrade head
```

Запустить тесты:

```bash
docker compose exec app uv run pytest
```

Запустить линтер:

```bash
uv run ruff check app tests migrations
```

Swagger UI доступен по адресу: http://localhost:8000/docs

## Примеры API

Создание количественной привычки:

```http
POST /habits
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "name": "Drink water",
  "habit_type": "quantitative",
  "schedule_type": "daily",
  "target_value": "2000",
  "unit": "ml"
}
```

Ответ:

```json
{
  "id": "0a49b9db-5c39-4f8a-9d22-ae5be139c2cb",
  "name": "Drink water",
  "habit_type": "quantitative",
  "schedule_type": "daily",
  "target_value": "2000.00",
  "unit": "ml",
  "weekdays": [],
  "weekly_target": null,
  "is_archived": false,
  "archived_at": null
}
```

Создание чек-ина:

```http
POST /habits/0a49b9db-5c39-4f8a-9d22-ae5be139c2cb/check-ins
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "value": "500",
  "logged_at": "2026-05-10T22:30:00Z"
}
```

Получение стрика:

```http
GET /habits/0a49b9db-5c39-4f8a-9d22-ae5be139c2cb/analytics/streak
Authorization: Bearer <access-token>
```

Ответ:

```json
{
  "current_streak": 4,
  "longest_streak": 9,
  "unit": "days"
}
```
