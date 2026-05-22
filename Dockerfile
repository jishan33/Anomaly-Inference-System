
# Dockerfile

From python:3.11-slim

# set workdir
WORKDIR /app

# install system deps (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements (we'll create this next) \
COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

# copy app
COPY . .

# expost internal port
EXPOSE 8000

# run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]