# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 10001 andrablicken \
    && useradd --uid 10001 --gid andrablicken --create-home andrablicken

COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then \
      PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir --requirement requirements.txt; \
    else \
      pip install --no-cache-dir --requirement requirements.txt; \
    fi

COPY --chown=andrablicken:andrablicken . .
RUN install -d -o andrablicken -g andrablicken -m 0700 /app/data

USER andrablicken
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
