<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tp="http://telepathy.freedesktop.org/wiki/DbusSpec#extensions-v0"
  exclude-result-prefixes="tp">

  <xsl:output method="text" indent="no" encoding="ascii"/>

  <xsl:template match="tp:errors/tp:error">
class <xsl:value-of select="translate(@name, '. ', '')"/>(DBusException):
    """\<xsl:value-of select="tp:docstring"/>
    """
    _dbus_error_name = '<xsl:value-of select="concat(../@namespace, '.', translate(@name, ' ', ''))"/>'
  </xsl:template>

  <xsl:template match="text()"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//tp:errors"/>
  </xsl:template>

  <xsl:template match="tp:errors">"""Exception classes, generated from the Telepathy spec

<xsl:for-each select="tp:copyright">
<xsl:value-of select="."/><xsl:text>
</xsl:text></xsl:for-each><xsl:text>
</xsl:text><xsl:value-of select="tp:license"/>

<xsl:value-of select="tp:docstring"/>
"""

from dbus import DBusException

__all__ = (
<xsl:for-each select="tp:error">
  <xsl:value-of select="concat('&quot;', translate(@name, '. ', ''),
    '&quot;',"/><xsl:text>&#10;</xsl:text>
</xsl:for-each>)

<xsl:apply-templates select="tp:error"/>
</xsl:template>

</xsl:stylesheet>

<!-- vim:set sw=2 sts=2 et noai noci: -->
