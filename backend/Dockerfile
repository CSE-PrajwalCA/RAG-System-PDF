FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY app/db_init.py /app/app/db_init.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
