FROM python:3.13-alpine

RUN mkdir -p /app/cogs && chmod g+rw /app && apk add --no-cache sqlite=3.49.2-r1 && pip install --no-cache-dir --upgrade pip==25.3

# Kubernetes (and by extension OKD) won't read python standardout if python's
# buffer is allowed to do stuff. Here we turn it off
ENV PYTHONUNBUFFERED=1

LABEL com.example.volumes.mountpoint="/app/db.sqlite" \
      com.example.volumes.description="Put runtime database here" \
      com.example.env.required="TOKEN, DB_FILE" \
      com.example.env.TOKEN.description="Discord bot token" \
      com.example.env.DB_FILE.description="Database file (default is db.sqlite, if you change this also change mount path)"

COPY cogs/*.py /app/cogs
COPY requirements.txt /app
COPY *.py /app

RUN pip --no-cache-dir install --requirement /app/requirements.txt

CMD [ "python", "-OO /app/main.py"]
