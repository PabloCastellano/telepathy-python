SUBDIRS = client server

telepathydir = $(pythondir)/telepathy
telepathy_PYTHON = \
	constants.py \
	errors.py \
	__init__.py \
	interfaces.py \
	utils.py \
	_version.py \
	$(BUILT_SOURCES)

spec_files= \
	_generated/Account_Interface_Avatar.py \
	_generated/Account_Manager.py \
	_generated/Account.py \
	_generated/Channel_Handler.py \
	_generated/Channel_Interface_Call_State.py \
	_generated/Channel_Interface_Chat_State.py \
	_generated/Channel_Interface_Destroyable.py \
	_generated/Channel_Interface_DTMF.py \
	_generated/Channel_Interface_Group.py \
	_generated/Channel_Interface_Hold.py \
	_generated/Channel_Interface_Media_Signalling.py \
	_generated/Channel_Interface_Messages.py \
	_generated/Channel_Interface_Password.py \
	_generated/Channel_Type_Contact_List.py \
	_generated/Channel_Type_Room_List.py \
	_generated/Channel_Type_Streamed_Media.py \
	_generated/Channel_Type_Text.py \
	_generated/Channel_Type_Tubes.py \
	_generated/Channel.py \
	_generated/Connection_Interface_Aliasing.py \
	_generated/Connection_Interface_Avatars.py \
	_generated/Connection_Interface_Capabilities.py \
	_generated/Connection_Interface_Contact_Capabilities.py \
	_generated/Connection_Interface_Contacts.py \
	_generated/Connection_Interface_Presence.py \
	_generated/Connection_Interface_Requests.py \
	_generated/Connection_Interface_Simple_Presence.py \
	_generated/Connection_Manager.py \
	_generated/Connection.py \
	_generated/Media_Session_Handler.py \
	_generated/Media_Stream_Handler.py \
	_generated/Properties_Interface.py

BUILT_SOURCES = \
	_generated/interfaces.py \
	_generated/constants.py \
	_generated/errors.py \
	_generated/__init__.py \
	${spec_files}

CLEANFILES = \
	_version.py \
	$(BUILT_SOURCES)

EXTRA_DIST = _version.py.in

distclean-local:
	rm -rf *.pyc _generated

XSLTPROC_OPTS = --nonet --novalid --xinclude
tools_dir = $(top_srcdir)/tools
spec_dir = $(top_srcdir)/spec

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
