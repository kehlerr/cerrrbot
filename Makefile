SHELL=./activate
dc_rm: SHELL=/bin/bash
DOCKER_COMPOSE_ARGS := -f ./docker/docker-compose-infra.yml -f ./docker/docker-compose-app.yml --env-file=.env
DOCKER_COMPOSE_APP_SERVICES := app-bot app-celery-worker

# Environment management commands
init: venv_install copy_env create_appdata
	echo "done"

venv_install:
	pip install --upgrade pip
	pip install -r .requirements/requirements.txt

create_appdata:
	@ls appdata || mkdir appdata

copy_env:
	cp sample.env .env

clean: dc_rm_all
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '__pycache__' -exec rm -rf {} \;
	@find ./ -name 'Thumbs.db' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	@rm -rf .cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf .tox/
	@rm -rf docs/_build
	@rm -rf .dev_meta

run:
	python bot/main.py

pretty:
	isort . && black . && flake8 .

# Docker
dc_build:
	@docker-compose $(DOCKER_COMPOSE_ARGS) build

logs:
	docker-compose $(DOCKER_COMPOSE_ARGS) logs $(DOCKER_COMPOSE_APP_SERVICES)

logs_recent:
	docker-compose $(DOCKER_COMPOSE_ARGS) logs --tail 10000 $(DOCKER_COMPOSE_APP_SERVICES)

logs_all:
	docker-compose $(DOCKER_COMPOSE_ARGS) logs

deploy: dc_stop dc_rm dc_up
	@echo "deploy finished"

dc_up:
	@docker-compose $(DOCKER_COMPOSE_ARGS) up -d

dc_stop:
	@docker-compose $(DOCKER_COMPOSE_ARGS) stop $(DOCKER_COMPOSE_APP_SERVICES)

dc_stop_all:
	@docker-compose $(DOCKER_COMPOSE_ARGS) stop

dc_rm: _dc_rm_containers _dc_rm_images
	@echo "docker cleaning done"

dc_rm_all: _dc_rm_containers_all _dc_rm_images
	@echo "docker cleaning done"

_dc_rm_containers:
	@CONTAINERS=$$(docker ps -a | grep cerrrbot_app | awk '{print $$1}'); \
	if [ -n "$$CONTAINERS" ]; then \
		echo $$CONTAINERS | xargs docker rm -f; \
	else \
		echo "No containers to remove."; \
	fi

_dc_rm_containers_all:
	docker-compose rm --force $(DOCKER_COMPOSE_ARGS)

_dc_rm_images:
	@IMAGES=$$(docker images | grep cerrrbot | awk '{print $$1}'); \
	if [ -n "$$IMAGES" ]; then \
		echo $$IMAGES | xargs docker rmi; \
	else \
		echo "No images to remove."; \
	fi