FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
COPY . .
# copy wait-for script included in repository
COPY wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for.sh
# Start gateway after ai_brain and reminder are healthy
CMD ["/app/wait-for.sh", "ai_brain:9004", "reminder:9002", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
