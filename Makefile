SHELL=./activate
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

clean:
	docker-compose rm --force
	docker images
	docker rmi '$(docker images | grep 'cerrrbot')'

deploydev:
	docker-compose up --force-recreate --no-deps --build

# Builder docker images
.PHONY: docker-build
dc_build:
	@docker-compose -f docker/docker-compose-app.yml build

dc_up:
	@docker-compose -f ./docker/docker-compose-infra.yml -f ./docker/docker-compose-app.yml --env-file=./docker/dev.env  up