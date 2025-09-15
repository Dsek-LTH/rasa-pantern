FROM python:3.13

RUN mkdir -p /app/cogs

COPY cogs/*.py /app/cogs
COPY requirements.txt /app
COPY *.py /app

RUN pip --no-cache-dir install --requirement /app/requirements.txt

CMD [ "python", "/app/main.py"]
