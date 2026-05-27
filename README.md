# Auth & RBAC API

Backend-приложение с собственной системой аутентификации и авторизации на базе **FastAPI + PostgreSQL + JWT**.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Framework | FastAPI 0.136 |
| Python | 3.14+ |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 |
| Аутентификация | JWT (access + refresh токены) via python-jose |
| Хэширование паролей | bcrypt (passlib) |
| Авторизация | Кастомный RBAC |
| Пакетный менеджер | uv |

---

## Быстрый старт

```bash
# 1. Запустить PostgreSQL и приложение
docker-compose up -d

# 2. Заполнить тестовыми данными
docker-compose exec app python -m app.seed

# Или без Docker:
uv sync
cp .env.example .env   # заполнить переменные
uvicorn app.main:app --reload
python -m app.seed
```

Документация API доступна по адресу: http://localhost:8000/docs

### Переменные окружения (`.env`)

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:port/db` |
| `SECRET_KEY` | Секретный ключ для подписи JWT |
| `ALGORITHM` | Алгоритм JWT (по умолчанию `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access-токена в минутах |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Время жизни refresh-токена в днях |

---

## Система разграничения прав доступа (RBAC)

### Концепция

Используется модель **Role-Based Access Control (RBAC)**:

- Каждый **пользователь** может иметь одну или несколько **ролей**.
- Каждая **роль** содержит набор **разрешений** (permissions).
- **Разрешение** — строка формата `ресурс:действие`, например `products:read`, `orders:write`.
- При запросе к защищённому эндпоинту система проверяет наличие нужного разрешения у ролей пользователя.

### Схема базы данных

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
│    users     │       │  user_roles  │       │      roles       │
├──────────────┤       ├──────────────┤       ├──────────────────┤
│ id           │◄──────│ user_id      │       │ id               │
│ last_name    │       │ role_id      │──────►│ name             │
│ first_name   │       └──────────────┘       │ description      │
│ patronymic   │                              └────────┬─────────┘
│ email        │                                       │
│ hashed_pass  │                              ┌────────▼─────────┐
│ is_active    │                              │ role_permissions  │
│ created_at   │                              ├──────────────────┤
│ updated_at   │                              │ role_id          │
└──────────────┘                              │ permission_id    │──────►┌─────────────┐
                                              └──────────────────┘       │ permissions │
                                                                          ├─────────────┤
                                                                          │ id          │
                                                                          │ name        │
                                                                          │ description │
                                                                          └─────────────┘
```

Дополнительно: таблица `token_blacklist` для инвалидации токенов при logout.

### Предустановленные роли и разрешения

| Роль | Разрешения |
|---|---|
| `admin` | `products:read`, `products:write`, `orders:read`, `orders:write`, `reports:read` |
| `manager` | `products:read`, `orders:read`, `orders:write`, `reports:read` |
| `viewer` | `products:read`, `orders:read` |

### Правила доступа

| Ситуация | HTTP-статус |
|---|---|
| Токен не передан / невалиден | `401 Unauthorized` |
| Токен валиден, но разрешения нет | `403 Forbidden` |
| Токен валиден, разрешение есть | `200 OK` + данные |
| Аккаунт деактивирован (`is_active=False`) | `401 Unauthorized` |
| Требуется `admin`, а роль другая | `403 Forbidden` |

---

## Модули системы

### 1. Аутентификация и профиль (`/auth`, `/users`)

| Метод | URL | Описание |
|---|---|---|
| POST | `/users/register` | Регистрация (имя, email, пароль) |
| POST | `/auth/login` | Вход → access + refresh токены |
| POST | `/auth/logout` | Выход (токен помещается в blacklist) |
| POST | `/auth/refresh` | Обновление access-токена |
| GET | `/users/me` | Просмотр своего профиля |
| PATCH | `/users/me` | Редактирование профиля |
| DELETE | `/users/me` | Мягкое удаление (`is_active=False`) |

### 2. Управление правами доступа — только `admin` (`/admin`)

| Метод | URL | Описание |
|---|---|---|
| GET | `/admin/permissions` | Список разрешений |
| POST | `/admin/permissions` | Создать разрешение |
| DELETE | `/admin/permissions/{id}` | Удалить разрешение |
| GET | `/admin/roles` | Список ролей с разрешениями |
| POST | `/admin/roles` | Создать роль |
| PATCH | `/admin/roles/{id}` | Обновить роль |
| DELETE | `/admin/roles/{id}` | Удалить роль |
| PUT | `/admin/roles/{id}/permissions` | Установить разрешения роли |
| GET | `/admin/users` | Список всех пользователей |
| PUT | `/admin/users/{id}/roles` | Установить роли пользователю |

### 3. Mock бизнес-объекты (`/business`)

| Метод | URL | Требуемое разрешение |
|---|---|---|
| GET | `/business/products` | `products:read` |
| POST | `/business/products` | `products:write` |
| GET | `/business/orders` | `orders:read` |
| GET | `/business/orders/{id}` | `orders:read` |
| GET | `/business/reports` | `reports:read` |
| GET | `/business/profile` | Любой авторизованный |

### 4. Служебный

| Метод | URL | Описание |
|---|---|---|
| GET | `/health` | Проверка работоспособности сервиса |

---

## Тестовые аккаунты (после `seed`)

| Роль | Email | Пароль |
|---|---|---|
| admin | admin@example.com | Admin1234! |
| manager | manager@example.com | Manager1234! |
| viewer | viewer@example.com | Viewer1234! |

---

## Структура проекта

```
app/
├── main.py              # FastAPI app + lifespan (создание таблиц)
├── seed.py              # Заполнение тестовыми данными
├── core/
│   ├── config.py        # Настройки из .env (pydantic-settings)
│   └── database.py      # SQLAlchemy async engine + get_db
├── models/              # SQLAlchemy ORM модели
│   ├── user.py
│   ├── role.py
│   ├── permission.py
│   ├── role_permission.py
│   ├── user_role.py
│   └── token_blacklist.py
├── schemas/             # Pydantic схемы запросов/ответов
│   ├── user.py
│   ├── auth.py
│   └── role.py
├── api/                 # FastAPI роутеры
│   ├── auth.py
│   ├── users.py
│   ├── admin.py
│   └── business.py
└── utils/
    ├── auth.py          # get_current_user, get_current_admin, require_permission
    ├── security.py      # JWT (python-jose) + bcrypt
    └── user.py          # Вспомогательная логика работы с пользователями
```
