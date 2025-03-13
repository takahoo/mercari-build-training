FROM alpine

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add --no-cache sqlite
# Install Python3 and Pip

COPY . /app

RUN addgroup -S mercari && adduser -S trainee -G mercari
# RUN chown -R trainee:mercari /path/to/db

#777によりどのユーザーも書き込み可
RUN mkdir -p /app/images && chmod -R 777 /app/images && chown -R trainee:mercari /app

ENV DATABASE_PATH=/app/db/database.db
USER trainee

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]

#docker build -t mercari-build-training/app