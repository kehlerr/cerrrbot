FROM python:3.10-bullseye as python_img

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /home/cerrrbot

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN python3 -m pip install --upgrade pip

COPY requirements.txt .
RUN pip3 wheel --no-cache-dir --no-deps --wheel-dir /home/cerrrbot/wheels -r requirements.txt

FROM python:3.10-bullseye

WORKDIR /home/cerrrbot

COPY --from=python_img /home/cerrrbot/wheels /wheels
COPY --from=python_img /home/cerrrbot/requirements.txt .

RUN pip3 install --no-cache /wheels/*

COPY bot/ .
COPY .env .
