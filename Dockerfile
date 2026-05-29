FROM python:3.11-slim

# Install ffmpeg (required for audio conversion)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure required directories exist
RUN mkdir -p downloads sessions

CMD ["python", "-u", "main.py"]
