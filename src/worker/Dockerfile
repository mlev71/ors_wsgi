FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-pip build-essential

COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


COPY cel.py .

#CMD ["ls"]
ENTRYPOINT ["celery", "-A",  "cel",  "worker"]
