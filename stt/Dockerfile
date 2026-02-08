FROM python:3.11-slim AS builder

WORKDIR /build

ENV PIP_DEFAULT_TIMEOUT=1000 \
  PIP_RETRIES=10 \
  PATH="/opt/venv/bin:${PATH}"

RUN apt-get update -y \
  && apt-get install -y --no-install-recommends build-essential portaudio19-dev \
  && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

# Install CPU-only torch first to avoid pulling large CUDA wheels.
RUN pip install --no-cache-dir --timeout 1000 --retries 10 \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.10.0 torchaudio==2.10.0 \
  && pip install --no-cache-dir --timeout 1000 --retries 10 \
    realtimestt==0.3.104 websockets numpy scipy

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
  PATH="/opt/venv/bin:${PATH}"

RUN apt-get update -y \
  && apt-get install -y --no-install-recommends libportaudio2 libsndfile1 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY server.py /app/server.py

EXPOSE 8001

CMD ["python", "server.py"]
