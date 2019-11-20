.PHONY: init test lint pretty precommit_install

BIN = ~/.pyenv/versions/3.8.0/envs/sqlalchemy-pydantic-field/bin/
CODE = sqlalchemy_pydantic_field
TESTS = tests

init:
	python3 -m venv .venv
	$(BIN)pip install --upgrade pip
	$(BIN)pip install --upgrade poetry
	$(BIN)poetry install

test:
	$(BIN)pytest --verbosity=2 --showlocals --strict --cov=$(CODE) $(args)

lint:
	$(BIN)flake8 --jobs 4 --statistics --show-source $(CODE) tests
	$(BIN)pylint --jobs 4 --rcfile=setup.cfg $(CODE)
	$(BIN)mypy $(CODE) tests
	$(BIN)black --py36 --skip-string-normalization --line-length=79 --check $(CODE) tests
	$(BIN)pytest --dead-fixtures --dup-fixtures

pretty:
	$(BIN)isort --apply --recursive $(CODE) $(TESTS)
	$(BIN)black --py36 --skip-string-normalization --line-length=79 $(CODE) $(TESTS)
	$(BIN)unify --in-place --recursive $(CODE) $(TESTS)

precommit_install:
	echo '#!/bin/sh\nmake lint test\n' > .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

bump_major:
	$(BIN)bumpversion major

bump_minor:
	$(BIN)bumpversion minor

bump_patch:
	$(BIN)bumpversion patch
