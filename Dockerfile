FROM python:3.11-slim

# Install ffmpeg (required for audio conversion)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Debug: show exactly what pytgcalls exposes so we can fix imports
RUN python -c "import pytgcalls; print('=== pytgcalls exports ==='); print(dir(pytgcalls)); print('=== __init__.py ==='); print(open(pytgcalls.__file__).read())"

COPY . .

# Ensure required directories exist
RUN mkdir -p downloads sessions

CMD ["python", "-u", "main.py"]
