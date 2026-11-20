FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 FASTEMBED_CACHE_PATH=/opt/fastembed
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# bake the embedding model into the image so containers start fast and offline
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"
COPY app app
COPY resumes /data/resumes
ENV RESUME_ROOT=/data/resumes
RUN useradd -m appuser && chown -R appuser /srv /opt/fastembed
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
