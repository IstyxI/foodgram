FROM python:3.9-slim

WORKDIR /app

COPY requirements/requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY ./entrypoint.sh .

RUN chmod +x ./entrypoint.sh

COPY . /app/backend

ENTRYPOINT ["bash", "./entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:7000", "foodgram.wsgi"]