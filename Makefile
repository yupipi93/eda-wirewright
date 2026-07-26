# wirewright — dev automation. `make help` lists targets.
.DEFAULT_GOAL := help
PY ?= python3

.PHONY: help install dev test lint fmt examples render docker docker-mcp clean

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## install the package
	$(PY) -m pip install .

dev:  ## editable install with dev + mcp extras
	$(PY) -m pip install -e '.[dev,mcp]'

test:  ## run the test suite
	$(PY) -m pytest -q

lint:  ## static checks
	ruff check src tests

fmt:  ## auto-fix lint
	ruff check --fix src tests

examples:  ## render every Python + JSON example into examples/out/
	@mkdir -p examples/out
	@for f in examples/*.py; do echo ">> $$f"; $(PY) "$$f"; done
	@for f in examples/json/*.json; do \
	  echo ">> $$f"; $(PY) -m wirewright.cli render "$$f" -o "examples/out/$$(basename $${f%.json}).png"; done

render:  ## render one contract:  make render IN=path.json OUT=out.png
	$(PY) -m wirewright.cli render "$(IN)" -o "$(OUT)"

docker:  ## build the container image
	docker build -t wirewright .

docker-mcp:  ## build + tag the MCP image (same image, different entrypoint)
	docker build -t wirewright .

clean:  ## remove build/test artefacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache \
	       examples/out **/__pycache__
