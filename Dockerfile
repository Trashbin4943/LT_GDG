FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "linguaproject.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "120"]