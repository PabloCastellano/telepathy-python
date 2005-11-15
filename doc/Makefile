all: spec.html

spec.html:
	chmod +x doc-generator.py
	PYTHONPATH=$(PWD)/.. ./doc-generator.py telepathy.server order >spec.html
