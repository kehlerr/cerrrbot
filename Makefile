SHELL=./make-venv
run:
	./main.py

deploy:
	docker-compose stop bot
	docker-compose rm --force bot
	docker-compose up --build -d bot

logs:
	docker-compose logs bot

pretty:
	isort . && black . && flake8 .
