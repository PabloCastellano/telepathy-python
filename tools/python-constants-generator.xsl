<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tp="http://telepathy.freedesktop.org/wiki/DbusSpec#extensions-v0"
  exclude-result-prefixes="tp">

  <xsl:output method="text" indent="no" encoding="ascii"/>

  <xsl:variable name="upper" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"/>
  <xsl:variable name="lower" select="'abcdefghijklmnopqrstuvwxyz'"/>

  <xsl:template match="tp:flags">
    <xsl:variable name="value-prefix">
      <xsl:choose>
        <xsl:when test="@value-prefix">
          <xsl:value-of select="@value-prefix"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="@name"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
# <xsl:value-of select="@name"/> (bitfield/set of flags, 0 for none)<xsl:text>
</xsl:text><xsl:apply-templates>
  <xsl:with-param name="value-prefix" select="$value-prefix"/>
</xsl:apply-templates>
      <xsl:text>
</xsl:text>
  </xsl:template>

  <xsl:template match="tp:enum">
    <xsl:variable name="value-prefix">
      <xsl:choose>
        <xsl:when test="@value-prefix">
          <xsl:value-of select="@value-prefix"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="@name"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
# <xsl:value-of select="@name"/><xsl:text>
</xsl:text><xsl:apply-templates>
  <xsl:with-param name="value-prefix" select="$value-prefix"/>
</xsl:apply-templates>LAST_<xsl:value-of select="translate($value-prefix, $lower, $upper)"/> = <xsl:value-of select="tp:enumvalue[position() = last()]/@value"/>
  </xsl:template>

  <xsl:template match="tp:flags/tp:flag">
    <xsl:param name="value-prefix"/>
    <xsl:variable name="name" select="translate(concat($value-prefix, '_', @suffix), $lower, $upper)"/>
    <xsl:value-of select="$name"/> = <xsl:value-of select="@value"/><xsl:text>
</xsl:text></xsl:template>

  <xsl:template match="tp:enum/tp:enumvalue">
    <xsl:param name="value-prefix"/>
    <xsl:variable name="name" select="translate(concat($value-prefix, '_', @suffix), $lower, $upper)"/>
    <xsl:value-of select="$name"/> = <xsl:value-of select="@value"/><xsl:text>
</xsl:text>
    </xsl:template>

  <xsl:template match="text()"/>

  <xsl:template match="/tp:spec">"""List of constants, generated from the Telepathy spec version <xsl:value-of select="tp:version"/><xsl:text>

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
