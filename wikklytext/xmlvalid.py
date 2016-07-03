"""
xmlvalid.py -- validity testing for XML texts

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
The XML character space as defined in section 2.2 of the XML specification:

u0000 - u0008 : Invalid (UTF-8: 0x00..0x08)
u0009 - u000A : OK
u000B - u000C : Invalid (UTF-8: 0x0b..0x0c)
u000D         : OK
u000E - u001F : Invalid (UTF-8: 0x0e..0x1f)
u0020 - uD7FF : OK
uD800 - uDFFF : Invalid (UTF-8: 0xed 0xa0 0x80 .. 0xed 0xbf 0xbf)
uE000 - uFFFD : OK
uFFFE - uFFFF : Invalid (UTF-8: 0xef 0xbf 0xbe .. 0xef 0xbf 0xbf)
U00010000 - U0010FFFF : OK

The valid UTF-8 character space is defined by:
	http://www.unicode.org/versions/Unicode5.0.0/ch03.pdf#G7404, Table 3-7
"""

def match_valid_xml(text, start, end):
	"""
	Find portion of given text that is:
		(1) Valid UTF-8
		(2) Valid to place in an XML stream
	
		text = UTF-8 encoded bytestring to test
		text[start] = first char to look at
		text[end-1] = last char to look at
		
	Returns number of valid bytes.
	"""
	if not isinstance(text, str):
		raise Exception("Expecting UTF-8 bytestring")
		
	i = start
	while i < end:
		#print "CHAR %s, x%x" % (text[i], ord(text[i]))
		# 00..7F
		if ord(text[i]) >= 0x00 and ord(text[i]) <= 0x7f:
			# u0000..u0008 = invalid
			if ord(text[i]) >= 0x00 and ord(text[i]) <= 0x08:
				#print "RET A"
				return (i-start)
				
			# u000B..u000C = invalid
			if ord(text[i]) >= 0x0b and ord(text[i]) <= 0x0c:
				#print "RET B"
				return (i-start)
				
			# u000e - u001f = invalid
			if ord(text[i]) >= 0x0e and ord(text[i]) <= 0x1f:
				#print "RET C"
				return (i-start)
				
			i += 1
			
		# C2..DF + 80..BF
		elif (end-i) >= 2 and ord(text[i]) >= 0xc2 and ord(text[i]) <= 0xdf and \
				ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0xbf:
			i += 2
			
		# E0 + A0..BF + 80..BF
		elif (end-i) >= 3 and ord(text[i]) == 0xe0 and \
			ord(text[i+1]) >= 0xa0 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf:
			i += 3
			
		# E1..EC + 80..BF + 80..BF
		elif (end-i) >= 3 and ord(text[i]) >= 0xe1 and ord(text[i]) <= 0xec and \
			ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf:
			i += 3
			
		# ED + 80..9F + 80..BF
		elif (end-i) >= 3 and ord(text[i]) == 0xed and \
			ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0x9f and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf:
				 
			i += 3
			
		# NOTE: ED A0 80 .. ED BF BF = invalid, but that range is already
		# excluded by the above test
			
		# EE..EF + 80..BF + 80..BF
		elif (end-i) >= 3 and ord(text[i]) >= 0xee and ord(text[i]) <= 0xef and \
			ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf:
			
			# uFFFE (EF BF BE) and uFFFF (EF BF BF) are invalid
			if ord(text[i]) == 0xef and ord(text[i+1]) == 0xbf and \
				(ord(text[i+2]) == 0xbe or ord(text[i+2]) == 0xbf):
				return (i-start)
				
			i += 3
		
		# F0 + 90..BF + 80..BF + 80..BF
		elif (end-i) >= 4 and ord(text[i]) == 0xf0 and \
			ord(text[i+1]) >= 0x90 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf and \
			ord(text[i+3]) >= 0x80 and ord(text[i+3]) <= 0xbf:
			i += 4
			
		# F1..F3 + 80..BF + 80..BF + 80..BF
		elif (end-i) >= 4 and ord(text[i]) >= 0xf1 and ord(text[i]) <= 0xf3 and \
			ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf and \
			ord(text[i+3]) >= 0x80 and ord(text[i+3]) <= 0xbf:
			i += 4
			
		# F4 + 80..BF + 80..BF + 80..BF
		elif (end-i) >= 4 and ord(text[i]) == 0xf4 and \
			ord(text[i+1]) >= 0x80 and ord(text[i+1]) <= 0xbf and \
			ord(text[i+2]) >= 0x80 and ord(text[i+2]) <= 0xbf and \
			ord(text[i+3]) >= 0x80 and ord(text[i+3]) <= 0xbf:
			i += 4
	
		# sidenote: the bytes C0-C1 and F5-FF can never appear in a UTF-8 stream,
		# but those are caught (along with other invalid sequences) here ...
		else:
			
			#print "RET D"
			return (i-start)
			
	# matched entire text
	#print "RET E"
	return (end-start)
			
def xml_replace_badchars(text, start, end, replace='\xef\xbf\xbd'):
	"""
	Replace invalid (for XML) chars in text with replacement character.
	
		text: UTF-8 encoded bytestring
		text[start] = first char to look at
		text[end-1] = last char to look at
		
	The default replacement char is \uFFFD (standard replacement char).
	"""
	# sanity
	if not isinstance(text,str) or not isinstance(replace,str):
		raise Exception("Inputs must be UTF-8")
		
	out = []
	i = start
	while i<end:
		# match next segment of valid chars
		n = match_valid_xml(text, i, end)
		# add matched segment
		out.append(text[i:i+n])
		i += n
		
		if i<end:
			# stopped on invalid char - replace it
			out.append(replace)
			i += 1
			
	return ''.join(out)
	
