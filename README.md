
# cerrrbot

**cerrrbot** - is a Telegram Bot, that helps collect and organize different data.

## Table of Contents

- [About](#about)
- [Features](#features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Running with venv](#running-with-venv)
  - [Running with Docker](#running-with-docker)
- [Configuration](#configuration)

## About
### Problem
Telegram became very convenient and solid application not only for messaging, but for consuming content in channels: news, notes, memes, media, etc. There is also personal chat `Saved messages`. I used this chat to store stuff from channels, other chats or just some texts which I need or liked. The more data was stored in this chat, the more it turned into a dump of a random data, where it was hard to separate useful data from some temporary data, which I needed some time ago, but not needed for now.
### Solution
So, I decided to create this bot for my personal purposes only, that extends default abilities of `Saved messages` chat. It can be considered as `Smart Saved messages`.

## Features
- temporary messages;
- removing messages after time;
- automatic download of medias;
- notifications;
- restricted messages receiving from one or several users;
- lots of others features can be added with plugins.

## Technology stack
- Python 3.11+
- Mongo DB 4.4
- Redis 7.2
- Celery 5.2
- aiogram 3.0

## Getting Started
### Prerequisites
You must have installed Python 3.11+ on your system and Docker if you prefer run applications with it.
Before running bot make sure you have running MongoDB and Redis locally or in docker containers.
#### Clone the repository
```
git clone git@github.com:kehlerr/cerrrbot.git
cd cerrrbot/
```

### Running with venv
1. Create virtual environment and activate it:
`python -m venv .venv && source activate`
2. Install requirements and init appdata directory:
`make init`
3. Change content of `.env` file. See configuration variables section below. The main thing, you have to set up `BOT_TOKEN` variable with token of your bot.
4.  Run bot:
`make run`

### Running with Docker
1. Copy `sample.env` to `.env`:
`make copy_env`
2. Change content of `.env` file. See configuration variables section below. The main thing, you have to set up `BOT_TOKEN` variable with token of your bot.
3. Run Docker containers:
`make dc_up` 

## Configuration
You can see example of configuration in `sample.env` and `bot/settings.py` file. Most of variables are pretty straightforward, here description some of them:
- `BOT_TOKEN` - token for your bot;
- `ALLOWED_USERS` - list of users, which allowed to send messages to bot;
- `DELETE_TIMEOUT_1`, `DELETE_TIMEOUT_2`, `DELETE_TIMEOUT_3`, `DELETE_TIMEOUT_4` - there are 4 options for delayed messages deleting.