# Base Image for builder
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Requirements
COPY .requirements/requirements.txt /
RUN pip install --upgrade pip
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Build the app image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt update -y
RUN apt install -y curl ffmpeg

# Create directory for the cerrrbot_admin user
ENV USER=cerrrbot_admin
ENV HOME=/home/$USER
RUN mkdir -p $HOME
WORKDIR $HOME

# Create directory for the bot data
ENV DATA_DIR_NAME=data
ENV DATA_DIR_PATH=${HOME}/${DATA_DIR_NAME}
RUN mkdir -p $DATA_DIR_PATH

# Create the app directory
ENV APP_DIR=bot
ENV APP_HOME=${HOME}/${APP_DIR}

# Copy source code to home
COPY $APP_DIR $APP_HOME

# Copy settings
COPY .env .

# Install Requirements
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

# Create the app user
RUN groupadd $USER && useradd -g $USER $USER
RUN chown -R $USER:$USER $HOME
USER $USER

WORKDIR ${APP_HOME}