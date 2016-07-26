venv: requirements.txt
	bin/venv-update venv= -ppython3.5 venv install= $(patsubst %,-r %,$^)

.PHONY: test
test: venv
	venv/bin/py.test tests
	venv/bin/flake8 _db_logic.py scrape.py server.py
