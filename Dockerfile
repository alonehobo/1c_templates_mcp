FROM python:3.12-slim

WORKDIR /app

# Зависимости устанавливаем отдельным слоем для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY app/ ./app/

# Папка с шаблонами — монтируется как volume
RUN mkdir -p /app/data/templates

ENV TEMPLATES_DIR=/app/data/templates
ENV PYTHONPATH=/app/app

EXPOSE 8023

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8023"]
