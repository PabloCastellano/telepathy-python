<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tp="http://telepathy.freedesktop.org/wiki/DbusSpec#extensions-v0"
  exclude-result-prefixes="tp">

  <xsl:output method="text" indent="no" encoding="ascii"/>

  <xsl:variable name="upper" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"/>
  <xsl:variable name="lower" select="'abcdefghijklmnopqrstuvwxyz'"/>

  <xsl:template match="interface">
    <xsl:variable name="u" select="translate(../@name, concat($lower, '/'), $upper)"/>
    <xsl:value-of select="$u"/> = '<xsl:value-of select="@name"/>'
</xsl:template>

  <xsl:template match="text()"/>

  <xsl:template match="/tp:spec">"""List of interfaces, generated from the Telepathy spec version <xsl:value-of select="tp:version"/><xsl:text>

</xsl:text><xsl:for-each select="tp:copyright">
<xsl:value-of select="."/><xsl:text>
</xsl:text></xsl:for-each><xsl:text>
</xsl:text><xsl:value-of select="tp:license"/>

<xsl:value-of select="tp:docstring"/>
"""
<xsl:apply-templates select="node"/>
</xsl:template>

</xsl:stylesheet>

<!-- vim:set sw=2 sts=2 et noai noci: -->
