venv: requirements.txt
	bin/venv-update venv= -ppython3.5 venv install= $(patsubst %,-r %,$^)

test: venv
	venv/bin/py.test tests
