# Интернет-магазин дверей - Backend API

Бэкенд для интернет-магазина дверей, разработанный на FastAPI с использованием SQLAlchemy, PostgreSQL, Redis и Celery.

## Технический стек

### Backend
- **FastAPI** - высокопроизводительный API фреймворк
- **Alembic** - для миграций базы данных
- **Pydantic** - для валидации данных
- **SQLAlchemy** - ORM для работы с базой данных

### Хранилища данных
- **PostgreSQL** - основная база данных
- **Redis** - для кэширования и хранения временных данных

### DevOps
- **Docker** и **Docker Compose** - для контейнеризации
- **Celery** - для асинхронных задач
- **Nginx** - для проксирования

## Структура проекта

```
app/
├── core/            # Конфигурация и общие компоненты
├── models/          # SQLAlchemy модели
├── schemas/         # Pydantic схемы
├── api/             # API эндпоинты
├── services/        # Бизнес-логика
├── utils/           # Вспомогательные функции
├── tasks/           # Celery задачи
└── cache/           # Работа с Redis кэшем

alembic/             # Миграции базы данных
nginx/               # Конфигурация Nginx
```

## Установка и запуск

### Локальная разработка

1. Клонировать репозиторий:
```bash
git clone <repository-url>
cd doors-shop-backend
```

2. Создать и активировать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установить зависимости:
```bash
pip install -r requirements.txt
```

4. Создать файл `.env` со следующими параметр