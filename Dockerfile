FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-pip build-essential

COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


RUN apt-get install -y uwsgi-plugin-python3
RUN apt-get install -y uwsgi-plugin-python

COPY app/components/cel.py .


COPY http.ini .
COPY app/ app/

EXPOSE 3031
ENTRYPOINT [ "uwsgi", "--ini", "http.ini"]
