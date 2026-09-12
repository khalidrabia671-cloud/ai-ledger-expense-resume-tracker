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

# Uploads folder banao aur permissions do (Hugging Face Spaces non-root user use karta hai)
RUN mkdir -p uploads && chmod -R 777 uploads

# Hugging Face Spaces port 7860 use karta hai
EXPOSE 7860

# App ko gunicorn (production server) se chalao
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
