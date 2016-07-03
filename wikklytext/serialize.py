"""
Serializing of ElementTrees, specialized for WikklyText nodes.

Public API:
	dumpxml(), loadxml()
	
This is *NOT* useful for general XML serialization, it will only
work with WikklyText trees.

Assumptions:
	* All attribute values must either be string/unicode, or
	  convertible with str().
	* Only tags beginning with 'Text' can have .text nodes.
	* Only tags NOT beginning with 'Text' can have attributes.
	* Only tags NOT beginning with 'Text' can have child nodes.

--------------------------------------------------------------------------
Copyright (C) 2007,2008 Frank McIngvale

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

def utf8(s):
	"If s is unicode, encode as UTF-8. If bytestring leave it alone. Else raise exception."
	#print "UTF8",repr(s)
	if isinstance(s, unicode):
		return s.encode('utf-8')
	elif isinstance(s, str):
		return s
	else:
		raise Exception("Need bytestring or unicode here.")
		
def xml_head():
	"Return XML stream header as UTF-8."
	return '<?xml version="1.0" encoding="utf-8"?>\n'
	
def xml_esc_attr(text):
	"""
	Escape text to be placed in an XML attribute.
	Adds quotes to the returned string.
	
	Usage:
		s = 'name=%s' % xml_esc_attr(text)
	"""
	return '"%s"' % xml_esc_text(text).replace('"', r'&quot;')
	
def xml_esc_text(text):
	"""
	Escape text to be placed in XML as PCDATA.
	Preserves whitespace where possible.
	"""
	escpairs = [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'),
			('\n', '&#x0a;'), ('\r', '&#x0d;'), ('\t', r'&#x09;')]
	for a,b in escpairs:
		text = text.replace(a,b)

	return text
	
def dumpxml(rootnode):
	"""
	Serialize Element to XML per the WikklyText rules.
	Returns XML as UTF-8 encoded bytestring.
	"""
	return xml_head() + _dumpxml(rootnode, 0)
	
def xml_remove_badchars(text):
	"""
	Replace any invalid (for XML) chars in text,
	returning new string.
	
	text must be a UTF-8 bytestring.
	"""
	from xmlvalid import xml_replace_badchars
	#print "T",repr(text)
	assert(isinstance(text,str))
	return xml_replace_badchars(text, 0, len(text))
	
def _dumpxml(node, indent):
	"Worker called by dumpxml()"
	# generate as UTF-8

	# indentation offset
	IOFS = '   '
	
	# only Text* nodes can have ".text". They cannot have attributes.
	if node.tag[:4] == 'Text':
		# .text can be a list of fragments, or a single string/unicode value
		if isinstance(node.text,list):
			text = ''.join(node.text) # will promote to unicode as appropriate
		else:
			text = node.text
			
		txt = xml_esc_text(xml_remove_badchars(utf8(text)))
		xml = '%s<%s>%s</%s>\n' % (indent*IOFS, utf8(node.tag), utf8(txt), utf8(node.tag))
	else:
		xml = '%s<%s' % (indent*IOFS, utf8(node.tag))
		for key,val in node.items():
			if not isinstance(val, str):
				val = str(val) # an integer, etc.
				
			xml += ' %s=%s' % (utf8(key),xml_esc_attr(xml_remove_badchars(utf8(val))))
	
		# if no subnodes, make self-closing for brevity
		if not len(node):
			xml += '/>\n'
			return xml
			
		xml += '>\n'
		
		for subnode in node:
			xml += _dumpxml(subnode, indent+1)
	
		xml += '%s</%s>\n' % (indent*IOFS, utf8(node.tag))
		
	return xml

def loadxml(xml):
	"""
	Load XML from buf, returning root Element.
	
	xml must be a UTF-8 encoded bytestring.
	
	Returns root Element of tree.
	
	(This is generic code, it will work on any XML not just WikklyText trees.)
	"""
	from wikklytext.base import StringIO, ElementTree

	sio = StringIO(xml)
	tree = ElementTree(None, sio)
	return tree.getroot()

def cmpelem(rootA, rootB):
	"""
	Compare two Elements, per WikklyText rules. All subnodes must match as well.
	
	Returns True/False if elements are the same.
	"""
	return _cmpelem(rootA, rootB)
	
def _cmpelem(elemA, elemB):
	# tags must match
	if elemA.tag != elemB.tag:
		return False
		
	# if Text* node, text must match
	if elemA.tag[:4] == 'Text':
		if elemA.text != elemB.text:
			return False
		else:
			# sanity
			assert(len(elemA) == 0)
			assert(len(elemB) == 0)
			
			# no subnodes by definition, so done
			return True
			
	# non-Text nodes
	else:
		# attrs must match
		for k in elemA.keys():
			if elemA.get(k) != elemB.get(k):
				return False
			
		# subnodes must match
		if len(elemA) != len(elemB):
			return False
			
		for i in range(len(elemA)):
			if _cmpelem(elemA[i], elemB[i]) is False:
				return False
				
		return True
	
	
		
	
