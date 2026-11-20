FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir gunicorn==20.0.4 gevent flask==2.3.3
COPY app.py .
CMD ["gunicorn", "--worker-class=gevent", "--workers=1", "--worker-connections=1000", "--bind", "0.0.0.0:5000", "app:app"]
