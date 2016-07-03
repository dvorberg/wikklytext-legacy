"""
wikklytext.macro.py: Parsing and evaluation of macros. Part of the WikklyText suite.

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

# public API
__all__ = ['split_macro_args', 'call_macro']

import re, sys
from wikklytext.error import exception_to_text
#import elementtree.ElementTree as etree
from wikklytext.base import WikError, Element, SubElement, iselement, Text, \
		ElementList, hex2int, oct2int, xmltrace
		
def char_escape(text):
	"""
	Handle escape sequence in text. Pass text AFTER leading '\'.
	Returns:
		(str_out, len)
		
		str_out = Translated value
		len = # of chars in 'text' used by escape sequence.
	"""
	# single chars that turn into other values
	c_from = "abfnrtv"
	c_to = "\a\b\f\n\r\t\v"
	if text[0] in c_from:
		return (c_to[c_from.index(text[0])],1)
	
	# \xHH hex escape (up to 2 chars, per Python standard)
	m = re.match('x([0-9a-h]{1,2})', text, re.I)
	if m:
		return (unichr(hex2int(m.group(1))), len(m.group(1))+1)
	
	# \NNN octal escape (up to 3 digits, per Python standard)
	m = re.match('([0-9]{1,3})', text, re.I)
	if m:
		return (unichr(oct2int(m.group(1))), len(m.group(1)))
	
	# \uHHHH unicode escape (only 4-digit unicode is supported on all Pythons)
	m = re.match('u([0-9a-h]{1,4})', text, re.I)
	if m:
		c = (unichr(hex2int(m.group(1))), len(m.group(1))+1)
		return c
		
	# return literal
	return (text[0],1)
	
def parse_macro_call(text):
	"""
	Parse a macro call
		 <<text text ...>>
	
	The input text must begin with '<<'. Parser will read up to and including the
	closing '>>'.
	
	Returns:
		(macrocall, txt_remainder)
	
	Where:
		* macrocall: Element('MacroCall') with macro args stored as subnodes.
		  Each subnode will be either:
		  	a. <TextMacroArg> - a literal text arg
			b. <MacroCall> - an inner macro call
		* txt_remainder = Text after macro call.
		 
	Handles:
		* Unquoted args (args delimited by whitespace)
		* Args quoted with ', ", triple-' or triple-" (triple quotes are a WikklyText extension)
		* Args quoted with <quote> ... </quote> (WikklyText extension)
		* Python-style escapes inside of quoted strings:
			  \a \b \f \n \r \t \v \' \" \\
			  xHH (hex, 1-2 chars) 
			  NNN (octal, 1-3 chars)
			  \uHHHH unicode escape (only 4-digit unicode is supported on all Pythons)

			  \{ANYCHAR} = ANYCHAR is passed through, if not in above list
			  
			  There is no need for the Python-style "\"+newline continuation since quoted strings are
			  allowed to span lines. The [\r\n] chars are saved as-is.
	
		* Linebreaks preserved inside quoted strings (outside of quoted strings, they are delimiters)
		* Allows string concatenation: 'aaa'bbb"ccc"ddd -> 'aaabbbcccddd'
		* Preserves empty args ('' and "")
		
	Raises WikError on:
		* Unterminated quotes.
		* Unterminated "\" inside a quote.
		* No closing >>
		* Error calling inner macro.
	"""
	# sanity check
	if text[:2] != '<<':
		raise Exception("Not a macro call.") # should never happen, so let it flow to top level
		
	in_arg = 0 # inside an arg
	in_quotechar = None # which quotechar I'm inside (', "", """, ''', or None)
	
	i = 2
	
	# args are stored here as subnodes
	macrocall = Element('MacroCall')
	out = u'' # current chunk of text
	while i < len(text):
		# check for end of macro
		if text[i:i+2] == '>>' and in_quotechar is None:
			break
			
		# look for nested macro call
		if re.match('<<[a-z]', text[i:], re.I) and in_quotechar is None:
			# if I have a partial arg, close before opening new macro call
			if in_arg:
				elem = Element('TextMacroArg')
				elem.text = out
				macrocall.append(elem)
				out = u''
				in_arg = 0
			
			# parse inner macro and add it as an arg
			inner_macrocall, txt_remainder = parse_macro_call(text[i:])
			macrocall.append(inner_macrocall)			
			i = 0
			text = txt_remainder
			continue # skip +=1 at bottom for clarity here
			
		if text[i] == '\\':
			in_arg = 1
			if in_quotechar:
				try:
					c,skip = char_escape(text[i+1:])
					out += c
					i += skip # skip extra char(s)
				except IndexError: # string ended with "\" inside a quoted string
					raise WikError("Macro statement ended inside unterminated quoted string",
									text[:80], '', text[i:]) 
									
			else:
				out += u'\\' # '\' is a regular char outside of a quoted string 
				
		elif text[i] in '\t \r\n':
			if not in_arg:
				i += 1 # skip whitespace outside of quoted strings
				continue
				
			if in_quotechar:
				out += text[i] # preserve whitespace inside a quoted string
			else:
				# end of arg - convert to Element and store.
				# NOTE: I'm using a special tag 'TextMacroArg' here. This purpose of this
				# is to catch any macro args that aren't processed by the macro. i.e. if
				# a "TextMacroArg" tag makes it through to the HTML writer, something is wrong.
				elem = Element('TextMacroArg')
				elem.text = out
				macrocall.append(elem)
				out = u''
				in_arg = 0
				
		# look for triple quotes
		elif text[i:i+3] in ["'''",'"""']:
			in_arg = 1
			if in_quotechar == text[i:i+3]: # end of quote?
				 # don't end arg - wait for whitespace break. this gives concatenation behaviour like:
				 #     "aaa"bbb'ccc'ddd ==> 'aaabbbcccddd'
				in_quotechar = None
			elif in_quotechar:
				out += text[i:i+3] # regular text inside of another quote
			else:
				in_quotechar = text[i:i+3] # begin quote
				
			# skip two extra chars
			i += 2

		# look for single-quotes
		elif text[i] in ["'",'"']:
			in_arg = 1
			# end of quote?
			if in_quotechar == text[i]:
				 # don't end arg - wait for whitespace break. this gives concatenation behaviour like:
				 #     "aaa"bbb'ccc'ddd ==> 'aaabbbcccddd'
				in_quotechar = None
			# in another quote?
			elif in_quotechar:				
				out += text[i] # regular char inside another quote
			else:
				in_quotechar = text[i] # begin squote

		# look for <quote>
		elif text[i:i+7] == '<quote>':
			in_arg = 1
			# in another quote?
			if in_quotechar:				
				out += text[i:i+7] # regular char inside another quote
			else:
				in_quotechar = text[i:i+7] # begin squote

			# skip 6 extra chars
			i += 6
			
		# look for </quote>
		elif text[i:i+8] == '</quote>':
			in_arg = 1
			# end of quote?
			if in_quotechar == '<quote>':			
				# don't end arg - wait for whitespace break. this gives concatenation behaviour like:
				#     "aaa"bbb'ccc'ddd ==> 'aaabbbcccddd'
				in_quotechar = None
			else:
				out += text[i:i+8] # regular text
				
			# skip 7 extra chars
			i += 7
			
		else:
			in_arg = 1
			out += text[i] # regular char
			
		i += 1
		
	if text[i:i+2] != '>>':
		raise WikError("No closing >> in macro statement", text[:80], '', text[i:])
		
	# the user might not have intended this, so let them know ...
	if in_quotechar:
		raise WikError("Macro statement ended inside a quoted string (current quote=%s)" % in_quotechar,
						text[:80], '', text[i:])
		
	# finish final partial arg if any
	if in_arg:
		# see note above about why this is 'TextMacroArg' instead of 'Text'
		elem = Element('TextMacroArg')
		elem.text = out
		macrocall.append(elem)
		
	# skip ending '>>'
	i += 2
	
	# collect all whitespace after this point
	k = i
	trailing = u''
	while len(text[k:]) and text[k] in ' \t\n':
		trailing += text[k]
		k += 1
	
	# if there is another macro call or a comment (i.e. non-visible markup), remove 
	# all intervening whitespace.
	# else, restore either a single space or a single \n depending on
	# what I found.
	if re.match(r'<<[a-z_]+', text[k:]) or re.match(r'/%', text[k:]):
		remainder = text[k:]
	elif trailing.find('\n\n') >= 0: # check before '\n'
		remainder = u'\n\n' + text[k:]
	elif '\n' in trailing:
		remainder = u'\n' + text[k:]
	elif len(trailing):
		remainder = u' ' + text[k:]
	else:
		remainder = text[k:]
			
	# the first element is really the macro name - return it as text
	#return (outlist[0].text, outlist[1:], remainder)
	return (macrocall, remainder)

# ensure modules in the cwd are found first
import sys, os
sys.path.insert(0,os.getcwd())

#def repr_macro_args(elements):
#	return ' '.join([repr(e.text) for e in elements])
	
def process_macro_result(wcontext, name, result):
	from wikklytext.eval import eval_wiki_text
	
	if iselement(result) and result.tag == 'ElementList':
		# already list-like, don't need to wrap
		pass
		
	# turn single values into list and handle below
	elif iselement(result) or isinstance(result, (unicode, str)):
		result = [result]
		
	elif isinstance(result, (list,tuple)):
		pass
		
	else:
		raise WikError("Calling <<%s>>\nMacros must return Elements or Unicode\nGot: %s, '%s'" % \
				(name, type(result), repr(result)))
		
	# now result can be handled as list/tuple - handle each element
	outnode = ElementList()
	for val in result:
		if iselement(val):
			outnode.append(val) # leave Elements alone
		elif isinstance(val, unicode): # parse Unicode -> Elements
			for e in eval_wiki_text(wcontext, val):
				outnode.append(e)
		elif isinstance(val, str):
			# note implicit unicode() conversion ... this is done for
			# convenience but macros should really return Unicode for
			# most robust code
			for e in eval_wiki_text(wcontext, unicode(val)):
				outnode.append(e)
		else:
			raise WikError("Calling <<%s>>\nMacros must return Elements or Unicode\nGot: %s, '%s'" % \
					(name, type(val), repr(val)))
	
	return outnode

from boodebr.util import load_module
from wikklytext.plugins import load_plugins
	
def call_macro(wcontext, name, elements):
	"""
	Given a macro arglist (parsed from split_macro_args, for example), call the
	macro and return the result.
	
	Returns list of elements that the macro returns. On error, will raise WikError.
	"""
	plugins = load_plugins(wcontext.plugin_dirs)

	func = None
	handled = False
	
	# if macro_handler is defined, try it first so caller can override all
	# internal macros
	if wcontext.macro_handler is not None:
		try:
			handled, result = wcontext.macro_handler(name, wcontext, *elements)
		except:
			raise WikError("ERROR CALLING MACRO <<%s>> with args:\n%s\n\n" % (name,xmltrace(elements)),
							'', exception_to_text(), '')
		
	# fall-through to set 'func' either way -- will check 'handled' at end
	
	# if not in restricted_mode, check for functions defined in embedded wikitext
	if func is None and not wcontext.restricted_mode:
		func = getattr(wcontext.mod_embedded, name, None)
		if func is not None and not callable(func):
			func = None # disregard non-functions

	# next, try unsafe macros if allowed to
	if func is None and not wcontext.restricted_mode:
		func = plugins.unsafe.get(name, None)
		
	# finally, try safe macros
	if func is None:
		func = plugins.safe.get(name, None)
	
	if func is None and not handled:
		raise WikError("Macro '%s' not defined, or not allowed to call." % name)
		
	# call with positional args and return value
	if not handled:
		try:
			result = func(wcontext, *elements)
		except:
			raise WikError("ERROR CALLING MACRO <<%s>> with args:\n%s\n\n" % (name,xmltrace(elements)),
							'', exception_to_text(), '')
			
	return process_macro_result(wcontext, name, result)

def insert_pycode(wcontext, txt):
	"Compile the given Python code, inserting any new functions into the callable list."
	try:
		# compile and exec code into module namespace -- this inserts any functions
		# and imported modules into mod_embedded namespace
		exec(txt) in wcontext.mod_embedded.__dict__
	except:
		raise WikError("Error compiling <?py ... ?> macro", txt[:80], exception_to_text(), '')
	
	# add some default globals
	eglobals = {
		'Element': Element, 'SubElement': SubElement, 'Text': Text,
		'WikError': WikError, 'FS_CWD': wcontext.var_get_text('$FS_CWD'),
		}

	# add names from __all__ in plugins as well
	plugins = load_plugins(wcontext.plugin_dirs)
	eglobals.update(plugins.embed)
	
	for k,v in eglobals.items():
		wcontext.mod_embedded.__dict__[k] = v
		
if __name__ == '__main__':
	from wikklytext.base import WikContext
	from wikklytext.parser import WikklyBaseContentParser
	
	# read test text from a file to make sure I'm not messing things up with quoting
	s = open('args.txt','rb').read()
	s = unicode(s)
	while s[:2] != '<<':
		s = s[1:]
		
	print "---- ORIGINAL TEXT ----"
	print repr(s)
	print "---- HERE ARE THE ARGS [as repr()] ----"
	wcontext = WikContext()
	p = WikklyBaseContentParser()
	wcontext.parser = p
	name,elements,remainder = split_macro_args(wcontext, s)
	print "MACRO-NAME:",name
	for node in elements:
		print repr(node.text)
	
	print "NOW SOME MORE STRINGS"
	for s in ['<<noargs>>', '<<noargs \t>>', '<<noargs \t\n\r >>', 
				'<<one-empty-arg "">>']:
		print "---- ORIGINAL TEXT ----"
		print repr(s)
		print "---- HERE ARE THE ARGS [as repr()] ----"
		wcontext = WikContext()
		p = WikklyBaseContentParser()
		wcontext.parser = p
		name,elements,remainder = split_macro_args(wcontext, s)
		print "MACRO-NAME:",name
		for node in elements:
			print repr(node.text)
	
	
