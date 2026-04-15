FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic httpx aiofiles

COPY backend/ backend/
COPY data/ data/
COPY evaluation/ evaluation/
COPY frontend/dist/ frontend/dist/

EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
