FROM python:3.11-slim
RUN mkdir -p /app
WORKDIR /app
# Copy shared models first
COPY shared /app/shared
# Copy service code
COPY services/habits /app/habits
WORKDIR /app/habits
# Install dependencies (pyproject.toml is now in /app/habits)
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
RUN mkdir -p /data
RUN apt-get update && rm -rf /var/lib/apt/lists/*
COPY services/habits/wait-for-advanced.py /app/wait-for-advanced.py
COPY services/habits/wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for-advanced.py /app/wait-for.sh || true
ENV PYTHONPATH=/app
CMD ["/app/wait-for.sh"]
