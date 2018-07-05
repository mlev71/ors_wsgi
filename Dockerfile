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

COPY src/components/cel.py .


COPY http.ini .
COPY src/ app/
COPY email_hashed.p .

EXPOSE 3031
ENTRYPOINT [ "uwsgi", "--ini", "http.ini"]


#EXPOSE 8080
#ENTRYPOINT [ "uwsgi", "--master", "--https", "0.0.0.0:8443,foobar.key,foobar.crt" ]

