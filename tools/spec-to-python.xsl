<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tp="http://telepathy.freedesktop.org/wiki/DbusSpec#extensions-v0"
  exclude-result-prefixes="tp">

  <xsl:output method="text" indent="no" encoding="ascii"/>

  <xsl:variable name="upper" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"/>
  <xsl:variable name="lower" select="'abcdefghijklmnopqrstuvwxyz'"/>

  <xsl:template match="interface">
    <xsl:variable name="u" select="translate(../@name, concat($lower, '/'), $upper)"/>
    <xsl:variable name="superclass">
      <xsl:choose>
        <xsl:when test="contains(/node/@name, '_Interface')
                        or contains(/node/@name, '/Channel_Type_')">
          <xsl:text>dbus.service.Interface</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>dbus.service.Object</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
class <xsl:value-of select="translate(/node/@name, '/_', '')"/>(<xsl:value-of select="$superclass"/>):
    """\<xsl:value-of select="tp:docstring"/>"""
<xsl:if test="contains(/node/@name, '_Interface')">
    def __init__(self):
        self._interfaces.add('<xsl:value-of select="@name"/>')
</xsl:if>

<xsl:apply-templates select="method"/>
<xsl:apply-templates select="signal"/>
  </xsl:template>

  <xsl:template match="method">
    @dbus.service.method('<xsl:value-of select="../@name"/>', in_signature='<xsl:for-each select="arg[@direction='in']"><xsl:value-of select="@type"/></xsl:for-each>', out_signature='<xsl:for-each select="arg[@direction='out']"><xsl:value-of select="@type"/></xsl:for-each>')
    def <xsl:value-of select="@name"/>(self<xsl:for-each select="arg[@direction='in']">, <xsl:value-of select="@name"/></xsl:for-each>):
        """<xsl:value-of select="tp:docstring"/>
        """
        raise NotImplementedError
  </xsl:template>

  <xsl:template match="signal">
    @dbus.service.signal('<xsl:value-of select="../@name"/>', signature='<xsl:for-each select="arg"><xsl:value-of select="@type"/></xsl:for-each>')
    def <xsl:value-of select="@name"/>(self<xsl:for-each select="arg">, <xsl:value-of select="@name"/></xsl:for-each>):
        """<xsl:value-of select="tp:docstring"/>
        """
        pass
  </xsl:template>

  <xsl:template match="/">
    <xsl:if test="node/interface[not(@tp:causes-havoc)]">
# Generated from the Telepathy spec
"""<xsl:for-each select="node/tp:copyright">
  <xsl:apply-templates/><xsl:text>
</xsl:text></xsl:for-each>
<xsl:apply-templates select="node/tp:license"/>
"""

import dbus.service

<xsl:apply-templates select="node/interface"/>

    </xsl:if>
  </xsl:template>

</xsl:stylesheet>

<!-- vim:set sw=2 sts=2 et noai noci: -->
