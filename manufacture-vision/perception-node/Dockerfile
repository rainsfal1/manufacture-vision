FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY src/ src/
COPY models/ models/

ENV PPE_MODEL_PATH=/app/models/ppe_detector.onnx
ENV FIRE_SMOKE_MODEL_PATH=/app/models/fire_smoke.onnx
ENV ZONES_CONFIG_PATH=/app/src/config/zones/zones.json
ENV INPUT_STREAM=/data/mock_videos/ppe/clip1.mp4
ENV DEBUG_OVERLAY=false
ENV DEBUG_OUTPUT_PATH=/tmp/debug_output.mp4

EXPOSE 9091

CMD ["python", "src/main.py"]
