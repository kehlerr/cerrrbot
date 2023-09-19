
# cerrrbot

**cerrrbot** is a Telegram Bot designed to help collect and organize various types of content.

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Running with venv](#running-with-venv)
  - [Running with Docker](#running-with-docker)
- [Configuration](#configuration)
- [Usage](#usage)
- [Plugins](#plugins)

## About
### Problem
As Telegram becomes very convenient and solid platform not only for messaging, but also for content consumption in channels, users often find themselves saving various types of content, such as news articles, memes, and media, to the `Saved messages` chat.
However, as the volume of saved data increases, it becomes challenging to distinguish valuable content from temporary or less important data in mentioned chat.

### Solution
So, I decided to develop this bot as a personal tool to enhance the functionality of the `Saved messages` chat. It can be considered as `Smart Saved messages`.

### Technology stack
- Python 3.11+
- Mongo DB 4.4
- Redis 7.2
- Celery 5.2
- aiogram 3.0

### Features
- temporary messages;
- automatic message removal after a set time;
- automatic media downloads;
- authorized messages receiving from specific user(s) only;
- [notifications](#notifications);
- extensibility through [plugins](#plugins);

## Getting Started
### Prerequisites
Before using cerrrbot, ensure you have the following prerequisites installed on your system:
- Python 3.11+;
- Docker *(optional)* - if you prefer to run applications in containers;

Also, make sure you have running locally or in docker containers these services:
- MongoDB;
- Redis *(optional)*.

#### Clone the repository
```
git clone --recurse-submodules git@github.com:kehlerr/cerrrbot.git
cd cerrrbot/
```

### Running with venv
1. Create virtual environment and activate it:
`python -m venv .venv && source activate`
2. Install the required dependencies and initialize the appdata directory::
`make init`
3. Edit the `.env` file to configure bot (see [Configuration section](#configuration) below) and ensure the `BOT_TOKEN` variable is set with your bot's token and `ALLOWED_USERS` filled with at least one *Telegram User ID*.
4.  Run bot:
`make run`

### Running with Docker
1. Copy `sample.env` file to `.env`:
`make copy_env`
2. Edit the `.env` file to configure bot (see [Configuration section](#configuration) below) and ensure the `BOT_TOKEN` variable is set with your bot's token and `ALLOWED_USERS` filled with at least one *Telegram User ID*.
3. Run Docker containers:
`make dc_up` 

## Configuration
You can find an example of the configuration in the `sample.env` and `bot/settings.py` files. Most variables are self-explanatory; however, here are explanations for some of them:
- `ALLOWED_USERS` - a list of user IDs permitted to send messages to the bot. Must contain at least one user ID;
- `DELETE_TIMEOUT_1`, `DELETE_TIMEOUT_2`, `DELETE_TIMEOUT_3`, `DELETE_TIMEOUT_4` - four options for delayed message deletion, see [Usage section](#usage) below about it.
- `TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION` -  a timeout before executing automatic default actions, see [Usage section](#usage) below about it;
- `DEFAULT_CACHE_KEY_PREFIX_NOTIFICATION` - prefix for keys in Redis used to select rows for sending notifications.

## Usage
### Sending Text Messages
When you send or forward some message with text only, Bot will reply on this message with message with menu  so-called *reply-message*. You can choose to just `Keep` the message in the chat or press the `Delete` button and select when the message will be deleted: immediately or after a specific time (defined in variables `DELETE_TIMEOUT_2`, `DELETE_TIMEOUT_3`, `DELETE_TIMEOUT_4`). If no action is taken, the message will be deleted after the time specified in `DELETE_TIMEOUT_1`. In both cases of deletion (automatic or custom), the bot's reply-message will also be deleted.

### Sending Messages with Media
When you send or forward message with media content (video, image, GIF, audio, file, voicemessage and videomessage), a `Download` button will be added to the *reply-message*. If the message contains multiple media items (so-called *group of medias*), a `Download all` button will be provided for downloading all items in the group, but if you press `Download`, the first media will be download only. All downloads will be stored in directory, specified in `DATA_DIR_PATH` variable.
By default, messages with media content will trigger the `Download` or `Download all` action (for *media groups*). If you don't press `Keep` or `Delete`, the media will be downloaded after a delay specified in the `TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION` variable.

### Sending Stickers
The logic for messages with stickers is similar to messages with media, but `Download` and `Download all` buttons are always provided. When you press `Download` the sent sticker is downloaded, in second case all stickers from *sticker pack* will be download in directory with name of this *sticker pack*.

### Notifications
Bot periodically checks the Redis DB cache for entries with a prefix specified in the `DEFAULT_CACHE_KEY_PREFIX_NOTIFICATION` variable. When it finds an entry, Bot sends a message containing the notification's content. To set up notifications, it's recommended to use [plugins](#plugins). However, you can also manually insert notification entries into the Redis DB.
The structure of notification dictionary should match the model of `Notification` from `bot/services/notifications/notification.py`:
- `text` *str*: text which will be sent in the message;
- `chat_id` *Optional[str]*: ID of the chat, where message will be sent; if not specified, message will be sent to the first user, which specified in variable `ALLOWED_USERS`;
- `reply_to_message_id` *Optional[str]*: if specified, notification message will be displayed as reply to message with such ID;
- `send_at` *Optional[int]*: UTC timestamp, when message should be sent;
- `send_count` *Optional[int]*: if specified value is more than 1, notification will be repeated several times;
- `repeat_in` *Optional[int]*: timeout between sending repeating notifications, used if specified `send_count`.

## Plugins
cerrrbot's functionality can be easily extended with plugins, allowing you to add new actions and features.
You can see examples of plugins which I developed for myself in [this repository](https://github.com/kehlerr/cerrrbot-plugins).

### Creating your own plugin
To create your plugin, follow these steps:

Create directory named with your name `<PLUGIN_NAME>` in `bot/plugins` with next structure:
```
-<PLUGIN_NAME>/
	- __init__.py
	- tasks.py
	- settings.py
	- <other modules>
	- ...
```
#### `__init__.py`
This file should contain:
```python
from  models  import  CustomMessageAction
from .tasks  import <Task1>, <...>

actions  = (
	CustomMessageAction(code="<...>", caption="<...>", order=<...>, method_args={
		"task_name": "plugins.<PLUGIN_NAME>.tasks.<Task1>",
		<...>
	}),
	...
)

tasks  = (<Task1>, <...>)
```
The main thing here is `actions` and `tasks` variables.
In `actions` you have to specify configuration of actions:
- `code` *str*: this is code associated with *Telegram inline-button*;
- `caption` *str*: this is caption, which will be displayed on *Telegram button*;
- `order` *int*: order for sorting buttons;
- `method_args` *dict*: this is keyword parameters, which will be passed into your task as arguments:
	- `task_name` *str*: this parameter must be specified in order to Celery discovers tasks;
	- `regex` *str*: regular expression, if message text passed for this value, then button of this action appears;
	- `is_instant` *Optional[bool]*: if set to `True`, then action will be executed in bot worker, otherwise it will be sent to Celery worker;
	- `parse_text_links` *Optional[bool]*: if set to `True`, then all *links entities* from message will be passed to task
	- `<...>` *Optional[Any]*: your custom parameters, which will be passed into task.

#### `tasks.py`
This file must contain Celery class-based tasks with logic of your plugin:
```python
from  celery  import  Task

<your imports here>

class Task1(Task):
	
	def  run(self, _, msgdoc) -> <...>:
		<your_logic_here>
```
Ideally, `run` method of task should return `AppResult` instance, which could be imported from `common.py`:
`from  common  import  AppResult`

### Sending notification in plugin
As mentioned above, you can easily set up notifications to be sent using your plugin's logic. Here's an example:
```python
import  asyncio
from  celery  import  Task

from  services.notifications  import  Notification, push_message_notification


class Task2(Task):
	def  run(self, _, msgdoc) -> <...>:
		<your_logic_here>
		asyncio.run(push_message_notification(
			Notification(
				text="Task2 finished!",
				<other_notification_parameters>
			)
		))
		...
```
See more about notifications parameters [above](#notifications).