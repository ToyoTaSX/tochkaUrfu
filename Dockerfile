# Базовый образ
FROM python:3.11-alpine

# Директория приложения
WORKDIR /app

# Зависимости Python
COPY ./app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Копируем все файлы приложения
COPY ./app /app

# Запуск FastAPI приложения через Uvicorn по порту 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
