FROM python:3.11-slim

WORKDIR /app

RUN apt-get update -y \
  && apt-get install -y --no-install-recommends build-essential git portaudio19-dev \
  && rm -rf /var/lib/apt/lists/*

ENV PIP_DEFAULT_TIMEOUT=1000 \
  PIP_RETRIES=10

RUN pip install --no-cache-dir --timeout 1000 --retries 10 realtimestt websockets numpy scipy

COPY server.py /app/server.py

EXPOSE 8001

ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]
