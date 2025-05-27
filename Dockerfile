FROM python:3.11-slim

# Устанавливаем базовые зависимости
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка Poetry
RUN pip install --no-cache-dir poetry

# Копируем только файлы, необходимые для установки зависимостей
COPY pyproject.toml /app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Добавляем необходимые библиотеки
RUN poetry add requests-html beautifulsoup4 lxml

# Копируем остальной код приложения
COPY . .

# Создаем необходимые директории
RUN mkdir -p static/css static/js static/images media/products media/categories

# Команда запуска приложения
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]