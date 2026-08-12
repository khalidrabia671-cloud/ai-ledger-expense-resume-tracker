# Python base image use karo
FROM python:3.11-slim

# Tesseract OCR system-level install karo (ye Docker ke andar chalta hai)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Working directory set karo
WORKDIR /app

# Requirements pehle copy karo (Docker caching ke liye behtar hai)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saara code copy karo
COPY . .

# Uploads folder banao
RUN mkdir -p uploads

# Port expose karo
EXPOSE 5000

# App ko gunicorn (production server) se chalao
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
