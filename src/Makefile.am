SUBDIRS = client server

telepathydir = $(pythondir)/telepathy
telepathy_PYTHON = \
	constants.py \
	errors.py \
	__init__.py \
	interfaces.py \
	utils.py

spec_dir = $(top_srcdir)/spec
spec_files := $(patsubst $(spec_dir)%.xml,_generated%.py,$(wildcard $(spec_dir)/*.xml))

BUILT_SOURCES = \
	_generated/interfaces.py \
	_generated/constants.py \
	_generated/errors.py \
	_generated/__init__.py \
	$(spec_files)

CLEANFILES = \
	_version.py \
	$(BUILT_SOURCES)

EXTRA_DIST = _version.py.in

versiondir = $(telepathydir)
nodist_version_PYTHON = _version.py

generateddir = $(telepathydir)/_generated
nodist_generated_PYTHON = $(BUILT_SOURCES)

distclean-local:
	rm -rf *.pyc _generated

XSLTPROC_OPTS = --nonet --novalid --xinclude
tools_dir = $(top_srcdir)/tools

_generated/interfaces.py:
	$(XSLTPROC) $(XSLTPROC_OPTS) -o $@ \
	    $(tools_dir)/python-interfaces-generator.xsl \
	    $(spec_dir)/all.xml

_generated/constants.py:
	$(XSLTPROC) $(XSLTPROC_OPTS) -o $@ \
	    $(tools_dir)/python-constants-generator.xsl \
	    $(spec_dir)/all.xml

_generated/errors.py:
	$(XSLTPROC) $(XSLTPROC_OPTS) -o $@ \
	    $(tools_dir)/python-errors-generator.xsl \
	    $(spec_dir)/all.xml

_generated/__init__.py:
	echo "# Placeholder for package" > $@

_generated/%.py:
	$(XSLTPROC) $(XSLTPROC_OPTS) -o $@ \
	    $(tools_dir)/spec-to-python.xsl \
	    $(spec_dir)/$*.xml
