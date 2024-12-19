FROM python:3.9-slim

WORKDIR /app

COPY requirements/requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY ./run_app.sh /app/run_app.sh

RUN chmod +x /app/run_app.sh

COPY . .

ENTRYPOINT ["bash", "./run_app.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:9000", "foodgram.wsgi"]