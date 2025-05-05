FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ADD . /app
WORKDIR /app

RUN uv sync --frozen

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "purchasing_concierge_demo.py"]
