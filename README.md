# Meeting Room Booking

Полноценное приложение для бронирования переговорных: FastAPI backend и веб-интерфейс. Пользователь видит доступные комнаты, создаёт бронь, а система не позволяет занять одну комнату на пересекающееся время.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-4169E1)

## Возможности

- создание и просмотр переговорных;
- создание, отмена и фильтрация бронирований;
- проверка пересечения временных слотов на уровне бизнес-логики;
- dashboard: занятость комнат, ближайшие встречи, загрузка за день;
- валидация входных данных, обработка ошибок, OpenAPI/Swagger;
- адаптивный веб-интерфейс, который работает через API;
- автотесты ключевой логики.

## Стек

`Python` · `FastAPI` · `SQLAlchemy` · `Pydantic` · `PostgreSQL` · `Docker` · `pytest` · HTML/CSS/JavaScript

## Запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Откройте http://127.0.0.1:8000. При первом запуске добавляются четыре демонстрационные переговорные. API-документация: http://127.0.0.1:8000/docs.

По умолчанию приложение использует SQLite (`booking.db`), чтобы его можно было запустить сразу. Для PostgreSQL задайте `DATABASE_URL`:

```bash
set DATABASE_URL=postgresql+psycopg://booking:booking@localhost:5432/booking
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

Приложение будет доступно на http://localhost:8000. Docker Compose поднимает PostgreSQL и передаёт строку подключения приложению.

## API

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `GET` | `/api/rooms` | список переговорных |
| `POST` | `/api/rooms` | создать переговорную |
| `GET` | `/api/bookings` | список броней с фильтрами |
| `POST` | `/api/bookings` | создать бронь |
| `PATCH` | `/api/bookings/{id}/cancel` | отменить бронь |
| `GET` | `/api/dashboard` | агрегированные KPI |

## Важное бизнес-правило

Новая бронь конфликтует с существующей, когда `new_start < existing_end AND new_end > existing_start`. Отменённые брони не блокируют слот. При конфликте API возвращает `409 Conflict` с понятным текстом.

## Что можно добавить дальше

JWT-роли, календарную сетку по дням, уведомления, Alembic-миграции и ограничение доступа к комнатам по офису.
