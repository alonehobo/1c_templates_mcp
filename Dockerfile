FROM python:3.12-slim

WORKDIR /app

# Зависимости устанавливаем отдельным слоем для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем bsl_console (Monaco Editor для 1С)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && git clone --depth 1 https://github.com/salexdv/bsl_console.git /tmp/bsl_console \
    && mv /tmp/bsl_console/src /app/bsl_console \
    && rm -rf /tmp/bsl_console \
    && apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Копируем исходники
COPY app/ ./app/

# Папка с шаблонами — монтируется как volume
RUN mkdir -p /app/data/templates

ENV TEMPLATES_DIR=/app/data/templates
ENV PYTHONPATH=/app/app

EXPOSE 8023

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8023"]
