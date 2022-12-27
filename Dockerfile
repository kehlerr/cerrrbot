FROM python:3.10-bullseye

WORKDIR /home/cerrrbot/

COPY . .
RUN pip3 install -r requirements.txt

