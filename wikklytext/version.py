"""
Various defines giving program name, version #, etc.
"""

NAME = "WikklyText"
AUTHOR = 'Frank McIngvale'

AUTHOR_EMAIL = "fmcingvale@gmail.com"

MAJOR = 1
MINOR = 6
SUBVER = 0
EXTRA = ""

if len(EXTRA):
	VSTR = "%d.%d.%d%s" % (MAJOR,MINOR,SUBVER,EXTRA)
else:
	VSTR = "%d.%d.%d" % (MAJOR,MINOR,SUBVER)
	

