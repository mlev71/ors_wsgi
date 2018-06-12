# Dockerfile for the full application
FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-pip build-essential

COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


RUN apt-get install -y uwsgi-plugin-python3
RUN apt-get install -y uwsgi-plugin-python

COPY http.ini .
COPY old_app/ app/

EXPOSE 8080

ENTRYPOINT [ "uwsgi", "--ini", "http.ini"]

