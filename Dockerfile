FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# openssh-client нужен для ssh-keygen (ключ приложения создаётся при первом запуске)
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN sed -i 's/\r$//' docker/app-entrypoint.sh && chmod +x docker/app-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker/app-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
