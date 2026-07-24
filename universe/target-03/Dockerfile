FROM python:3.11-slim

RUN pip install flask pyjwt

COPY app/ /app/
WORKDIR /app

EXPOSE 5000

CMD ["python3", "server.py"]
