FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
# Install Python3 and Pip

#port指定
EXPOSE 900
CMD ["python", "app.py"]

#docker build -t mercari-build-training/app