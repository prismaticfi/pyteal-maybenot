REPO = pyteal-maybenot

clean:
	find . -name '__pycache__' | xargs rm -rf
	find . -name '*.pyc' -delete
	rm -rf .pytest_cache

image: clean
	docker compose -p $(REPO) build

tests: 
	docker compose -p $(REPO) run test poetry run pytest

ci_tests:  # Run tests on Github
	docker-compose -p $(REPO) run --rm test poetry run pytest -v -n 2
