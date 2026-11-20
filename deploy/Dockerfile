# Bareeq test server: the Django server + the browser version of the app, in
# one box that does not touch anything else on the machine.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0
COPY backend/ /app/
COPY deploy/web-build/ /web/
ENV APP_WEB_DIR=/web
