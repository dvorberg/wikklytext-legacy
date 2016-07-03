"""
util.py: Utilities

Copyright (C) 2008 Frank McIngvale

Contact: fmcingvale@gmail.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
"""

def content_type_for_xhtml(headers):
	"""
	Return the Content-Type header that should be used for XHTML.
	'headers' are the request headers.
	"""
	# set the W3C recommended media type for XHTML in an XML container *if* the
	# browser supports it. (IE7 for one won't handle application/xhtml+xml)
	
	# HOWEVER ... in practice this causes problems ... try again later
	#if 'application/xhtml+xml' in headers.get('Accept',''):
	#	return 'application/xhtml+xml'
	#else:
	#	return 'text/html'
	
	return 'text/html'
		
def itemText(wiki, itemname, default=u''):
	"Load a wiki item, returning .content for item or default if item not found."
	node = wiki.getitem(itemname)
	if node is None:
		return default
	else:
		return node.content

