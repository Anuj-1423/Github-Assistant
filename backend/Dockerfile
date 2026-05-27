FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hack to get the frontend folder since Docker build context is restricted to /backend
RUN git clone https://github.com/Anuj-1423/Github-Assistant.git /tmp/repo && \
    cp -r /tmp/repo/frontend /app/frontend && \
    rm -rf /tmp/repo

EXPOSE 8000

# Entry point updated from app.main to src.main
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"
