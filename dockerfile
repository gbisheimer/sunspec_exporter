FROM python:3-alpine3.12

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt 

COPY . .

ENV LISTEN_PORT=8080

EXPOSE 8080

CMD [ "python", "./sunspec_exporter.py" ]