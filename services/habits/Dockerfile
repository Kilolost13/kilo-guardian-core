FROM python:3.11-slim
RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
COPY . .
RUN mkdir -p /data
RUN apt-get update && rm -rf /var/lib/apt/lists/*
COPY ./wait-for-advanced.py /app/wait-for-advanced.py
COPY wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for-advanced.py /app/wait-for.sh || true
CMD ["/app/wait-for.sh"]
