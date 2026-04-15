.PHONY: install run test test-verbose cli lint docker-up docker-down smoke

install:
	pip install -r requirements.txt

run:
	python run.py

test:
	PYTHONPATH=. pytest -q

test-verbose:
	PYTHONPATH=. pytest -v

cli:
	python dentist_agent.py

lint:
	python -m compileall app tests dentist_agent.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

smoke:
	PYTHONPATH=. python scripts/smoke_test.py
