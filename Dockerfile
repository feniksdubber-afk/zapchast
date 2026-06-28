FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /app papkasini Python path'ga qo'shamiz — import xatoligi shu bilan hal bo'ladi
ENV PYTHONPATH=/app

CMD ["python", "bot.py"]
