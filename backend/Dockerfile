FROM python:3.11-slim

WORKDIR /app

# install system deps (curl สำหรับ healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# install dependencies ก่อน (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source
COPY . .

# สร้าง folder สำหรับ SQLite
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
