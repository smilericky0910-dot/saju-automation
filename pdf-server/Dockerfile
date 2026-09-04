FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY pdf_server.py .
COPY pdf_report.py .

ENV PORT=8080
EXPOSE 8080

# Playwright sync API는 요청당 하나의 스레드에서 안전하게 동작하므로,
# gunicorn 워커는 sync(threads=1 기본값)로 두고 프로세스 수만 늘린다.
CMD exec gunicorn --bind :$PORT --workers 2 --timeout 180 pdf_server:app
