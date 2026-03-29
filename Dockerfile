FROM python:3.12-slim

WORKDIR /app

# bsl_console (Monaco Editor для 1С) — скачиваем средствами Python
RUN python3 -c "\
import urllib.request, zipfile, io; \
data = urllib.request.urlopen('https://github.com/salexdv/bsl_console/archive/refs/heads/master.zip').read(); \
zipfile.ZipFile(io.BytesIO(data)).extractall('/tmp')" \
    && mv /tmp/bsl_console-master/src /app/bsl_console \
    && rm -rf /tmp/bsl_console-master

COPY app/ ./app/
RUN mkdir -p /app/data/templates

ENV TEMPLATES_DIR=/app/data/templates
ENV PYTHONPATH=/app/app

EXPOSE 8023

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8023/health')" || exit 1

CMD ["python", "/app/app/main.py"]
