venv: requirements.txt
	bin/venv-update venv= -ppython2.7 venv install= $(patsubst %,-r %,$^)

test: venv
	venv/bin/py.test tests
