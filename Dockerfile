FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY wx_publish_gateway ./wx_publish_gateway
COPY pyproject.toml README.md ./

EXPOSE 8000
CMD ["uvicorn", "wx_publish_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
