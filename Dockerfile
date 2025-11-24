# Python 3.12 slim 이미지 사용
FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 설치 (최소한만)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (무거운 ML 라이브러리 제외)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    Django==5.1.2 \
    django-ninja==1.5.0 \
    django-ninja-jwt==5.3.0 \
    gunicorn==21.2.0 \
    django-environ==0.11.2 \
    django-storages==1.14.2 \
    boto3==1.34.34 \
    pydub==0.25.1 \
    numpy==1.26.4 \
    requests==2.32.3 \
    PyYAML==6.0.2 \
    python-dateutil==2.9.0

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput || true

# 포트 노출
EXPOSE 8080

# 시작 스크립트 생성 (마이그레이션 + 서버 실행)
RUN echo '#!/bin/bash\n\
python manage.py migrate --noinput\n\
exec gunicorn linguaproject.wsgi:application --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120\n\
' > /app/start.sh && chmod +x /app/start.sh

# 애플리케이션 실행
CMD ["/app/start.sh"]
