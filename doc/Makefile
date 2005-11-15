all: spec.html

spec.html: $(PWD)/../telepathy/*.py $(PWD)/../telepathy/server/*.py
	chmod +x doc-generator.py
	PYTHONPATH=$(PWD)/.. ./doc-generator.py telepathy.server order >spec.html
