FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* requirements.txt* ./
RUN pip install -U uv || pip install pip
RUN if [ -f uv.lock ]; then uv sync --frozen; elif [ -f requirements.txt ]; then pip install -r requirements.txt; fi

COPY . .

CMD ["uv", "run", "src/main.py"]
