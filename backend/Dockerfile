FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY admin.py auth.py app.py db.py provider.py image_upload.py portrait_prompt.py alembic.ini ./
COPY migrations ./migrations
RUN mkdir -p data/media
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app:app --host 0.0.0.0 --port 8000"]
