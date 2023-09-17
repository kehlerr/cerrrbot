SHELL=./activate

# Environment management commands
init: venv_install copy_env create_appdata
	echo "done"

venv_install:
	pip install --upgrade pip
	pip install -r .requirements/requirements.txt

create_appdata:
	@ls appdata || mkdir appdata

clean:    ## Clean unused files.
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
	docker-compose rm --force
	docker images
	docker rmi '$(docker images | grep 'cerrrbot')'

copy_env:
	cp sample.env .env

run:
	python bot/main.py

deploy:
	docker-compose stop bot
	docker-compose rm --force bot
	docker-compose up --build -d bot

log:
	docker-compose logs bot

pretty:
	isort . && black . && flake8 .

deploydev:
	docker-compose up --force-recreate --no-deps --build

# Builder docker images
.PHONY: docker-build
dc_build:
	@docker-compose -f docker/docker-compose-app.yml build

dc_up:
	@docker-compose -f ./docker/docker-compose-infra.yml -f ./docker/docker-compose-app.yml --env-file=.env up