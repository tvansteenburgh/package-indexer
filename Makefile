clean:
	find . -name __pycache__ -type d -exec rm -r {} +
	find . -name *.pyc -delete
	rm -rf .tox/
	rm -rf do_indexer.egg-info/
	rm -f .coverage

serve:
	python3 -m indexer.main 2>&1 -l DEBUG -p 8080 -o 0.0.0.0 -i /tmp| tee /tmp/indexer.log

.PHONY: clean serve
