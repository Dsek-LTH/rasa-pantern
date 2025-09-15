FROM python:3.13

RUN mkdir -p /app/cogs && chmod g+rw /app

# Kubernetes (and by extension OKD) won't read python standardout if python's
# buffer is allowed to do stuff. Here we turn it off
ENV PYTHONUNBUFFERED=1

COPY cogs/*.py /app/cogs
COPY requirements.txt /app
COPY *.py /app

RUN pip --no-cache-dir install --requirement /app/requirements.txt

CMD [ "python", "/app/main.py"]
