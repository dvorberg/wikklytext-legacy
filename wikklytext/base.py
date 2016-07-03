"""
wikklytext.base.py: Base classes and functions. Part of the WikklyText suite.

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

# get the best StringIO implementation (other modules import StringIO from here)
try: from cStringIO import StringIO
except: from StringIO import StringIO

# include parts of ElementTree I need so other modules can import them.
# try addon package first -- assume user wants that version since they
# went to the trouble of installing it
try:
	# try addon package -- C version first
	from elementtree.cElementTree import ElementTree, Element, SubElement, iselement, iterparse
	#print "GOT cElementTree (addon)"
except:
	try:
		# try Python version
		from elementtree.ElementTree import ElementTree, Element, SubElement, iselement, iterparse
		#print "GOT PyElementTree (addon)"
	except:
		try:
			# Python 2.5 comes with ElementTree -- try C version first
			from xml.etree.cElementTree import ElementTree, Element, SubElement, iselement, iterparse
			#print "GOT cElementTree (builtin)"
		except:
			# try Python version
			from xml.etree.ElementTree import ElementTree, Element, SubElement, iselement, iterparse
			#print "GOT PyElementTree (builtin)"
			# else, raise exception
			
def hex2int(hexstr):
	"Convert given hex string to int"
	return int(hexstr,16)
	
def oct2int(octstr):
	"Convert given octal string to int"
	return int(octstr,8)
	
class WikError(Exception):
	"""
	General-purpose exception raised when errors occur during parsing 
	or XML/HTML generation.
	
	'message' is brief error message (no HTML)
	'looking_at' is text near/after error location
	'trace' is exception trace (raw text) , or '' if no exception occurred.
	'remainder' is buffer after point of error.
	"""
	def __init__(self, message, looking_at=None, trace=None, remainder=''):
		Exception.__init__(self, message)
		self.message = message
		self.looking_at = looking_at
		self.trace = trace
		self.remainder = remainder

	def __str__(self):
		s = "WikError:"
		s += 'Message:\n%s\n' % self.message
		s += 'Looking at:\n%s\n' % self.looking_at
		s += 'Traceback:\n%s\n' % self.trace
		return s

class WikContext(object):
	"""
	An instance of WikContext is passed to around through the lexer, parser,
	and called macros. This allows saving/retrieve any persistent data in a thread safe way.
	"""
	def __init__(self, restricted_mode=True, max_runtime=-1, url_resolver=None,
					plugin_dirs=None, rendercache=None, macro_handler=None):
		import sys, new
		import wikklytext.coremacros
		from time import time
		
		# in restricted_mode, unsafe features are turned off
		self.restricted_mode = restricted_mode

		# calculate stop time
		if max_runtime < 0:
			self.stoptime = time() + 1000000 # "unlimited"
		else:
			self.stoptime = time() + max_runtime
		
		# URL resolver -- see wikklytext.util.default_URL_resolver() for interface.
		# (If url_resolver is None, a default resolver will be used instead.)
		self.url_resolver = url_resolver
		
		# passed as plugdirs to plugins.load_plugins(), if not None
		self.plugin_dirs = plugin_dirs
		
		# an instance of a class in wikklytext.cache to do caching of renders
		from wikklytext.cache import NullCache
		self.rendercache = rendercache or NullCache()
		
		# if given, this is a function that is called just like
		# a macro, except it also gets a name argument (the name
		# of the macro to be called):
		#      handled, result = macro_handler(name, context, *elements)
		#
		# returns:
		#    handled: True/False if macro was handled
		#    result: the macro return value, ready to be processed
		#            by macro.process_macro_result().
		#
		# macro_handler() is responsible for permission checking who can 
		# call its handled macros.
		self.macro_handler = macro_handler
		
		# module namespace for embedded code (<?py ... ?>)
		name = 'wikklytext.macroEmbedded'
		if not sys.modules.has_key(name):
			mod = new.module(name)
		else:
			mod = sys.modules[name]
			
		self.mod_embedded = mod
		
		# the 'set' macro is somewhat special, so reserve its storage now ...
		
		# .uservars are for <<set NAME ...>>
		self.uservars = {}
		
		# .sysvars are for <<set $NAME ...>>
		# (the '$' is not stored but must be passed to get/set them)
		self.sysvars = {}
		
		# URL prepended to relative URLs (in default_URL_resolver)
		self.var_set_text("$BASE_URL", "")
		# substituted for $SITE in URL; no fixed meaning.
		self.var_set_text("$SITE_URL", "")
		# should paragraphs reflow around line breaks?
		self.var_set_int("$REFLOW", 1)
		# title for standalone documents
		self.var_set_text("$TITLE", "")
		# should external links open in a new window?
		self.var_set_int("$LINKS_NEW_WINDOW", 1)
		# directory to treat as current directory for relative file paths
		# (used by macros like <<include>>)
		self.var_set_text('$FS_CWD', os.getcwd())
		
	def add_runtime(self, seconds):
		"Add additional runtime before parser/generator will stop."
		self.stoptime += seconds
		
	def copy(self):
		c = WikContext(self.restricted_mode, url_resolver=self.url_resolver,
					plugin_dirs=self.plugin_dirs, rendercache=self.rendercache,
					macro_handler=self.macro_handler)
		# want to use same module namespace so <?py code is visible in recursive calls
		c.mod_embedded = self.mod_embedded
		
		# keep same stoptime, do not restart counter
		c.stoptime = self.stoptime
		
		# copy all uservars and sysvars to new context
		c.update(self)
		return c
		
	def make_digest(self, wikitext):
		"""
		Create a digest, suitable for use by the wikklytext.cache classes,
		for the given wikitext in this context (taking into account all
		uservars & sysvars since those affect rendering).
		"""
		from boodebr.util import makeSHA
		from wikklytext.serialize import utf8

		s = makeSHA()
		
		# account for all variables that can affect rendering.
		#
		# the user may have defined additional vars that affect how macros work,
		# but since macro results are not cached, that's OK.
		names = ['$BASE_URL', '$SITE_URL', '$REFLOW', '$TITLE', '$LINKS_NEW_WINDOW',
				'$FS_CWD']
		
		names.sort()

		for name in names:
			s.update(utf8(u'%s:%s' % (name,self.var_get_text(name))))
			
		s.update('%s' % str(self.restricted_mode))
		
		# add in wikitext itself
		s.update(utf8(wikitext))
		return s.hexdigest()
		
	def update(self, context):
		self.uservars.update(context.uservars)
		self.sysvars.update(context.sysvars)
		
	def var_set_int(self, name, value):
		self.var_set_text(name, '%d' % value)
		
	def var_set_text(self, name, text):
		elist = ElementList()
		elist.append(Text(text))
		self.var_set(name, elist)
		
	def var_get_text(self, name):
		"Get a variable as text."
		# get variable as element(s)
		e = self.var_get(name)
		
		# grab first Text node
		i = e.getiterator('Text')
		try:
			node = i.next() # cElementTree returns generator
		except AttributeError:
			node = i[0] # ElementTree returns list
			
		return node.text

	def var_get_int(self, name):
		"Get a variable as an integer. Raises an exception if variable not an int."
		# get variable as element(s)
		e = self.var_get(name)
	
		# grab first Text node
		i = e.getiterator('Text')
		try:
			node = i.next() # cElementTree returns generator
		except AttributeError:
			node = i[0] # ElementTree returns list
			
		return int(node.text)

	# -*- Internal API -*-
	def var_set(self, name, elements):
		"Raw set of named variable, as an ElementList"
		#from serialize import dumpxml
		#print "var_set %s, %s" % (name, dumpxml(elements))
		
		# '$' vars go into .sysvars
		if name[0] == '$': 
			# strip '$'
			self.sysvars[name[1:]] = elements
		else: 
			# others go into .uservars
			self.uservars[name] = elements
	
	def var_get(self, name):
		"Raw get of named variable, as an ElementList"
		if name[0] == '$':
			elements = self.sysvars.get(name[1:], Text('* ERROR in get() - unknown var $%s *' % name[1:]))
		else:
			elements = self.uservars.get(name, Text('* ERROR in get() - unknown var %s *' % name))
	
		return elements

	def var_user_keys(self):
		"Get names of all user variables"
		return self.uservars.keys()
		
	def var_sys_keys(self):
		"Get names of all system variables"
		return ['$'+name for name in self.sysvars.keys()]
		
def xmltrace(elements):
	"Generate a debugging trace for an Element or list of Elements."
	
	s = u"Elements:\n".encode('utf-8')
	for i,node in enumerate(elements):
		sio = StringIO()
		tree = ElementTree(node)
		tree.write(sio, 'utf-8')
		s += ("#%d: " % i).encode('utf-8') + sio.getvalue() + u'\n'.encode('utf-8')
		
	return s

# regex to catch a UTF-8 multibyte sequence
# Ref: http://www.unicode.org/versions/Unicode4.0.0/ch03.pdf#G7404
re_UTF8_mbchar = '([\xc2-\xdf][\x80-\xbf])|(\xe0[\xa0-\xbf][\x80-\xbf])|([\xe1-\xec][\x80-\xbf][\x80-\xbf])|' + \
				'(\xed[\x80-\x9f][\x80-\xbf])|([\xee-\xef][\x80-\xbf][\x80-\xbf])|' + \
				'(\xf0[\x90-\xbf][\x80-\xbf][\x80-\xbf])|([\xf1-\xf3][\x80-\xbf][\x80-\xbf][\x80-\xbf])|' + \
				'(\xf4[\x80-\x8f][\x80-\xbf][\x80-\xbf])'

def detect_encoding(buf):
	"""
	Attempt to detect encoding of the given buffer. 'buf' should be
	a raw bytestring (encoded Unicode value).
	
	Returns:
		(encoding, srcbuf)
		
	Where:
		encoding = string to pass to unicode() to decode srcbuf,
		           or None if encoding can't be detected.
		srcbuf = portion of buf to decode
	"""
	import re
	# First check for a Unicode BOM
	# ('codecs' defines these, but I had already hardcoded them, 
	# so I'm leaving them alone)
	
	# UTF-16 BE
	if buf[:2] == '\xfe\xff':
		return ("UTF-16BE", buf[2:])
		
	# UTF-16 LE
	if buf[:2] == '\xff\xfe':
		return ("UTF-16LE", buf[2:])
		
	# UTF-8-SIG
	if buf[:3] == '\xef\xbb\xbf':
		return ("UTF-8", buf[3:])

	# See if encoding is specified with "/% encoding: STRING %/"
	m = re.search('^\s*/%\s*encoding:\s*(\S+)\s*%/', buf, re.M)
	if m:
		# use given encoding
		return (m.group(1), buf)
			
	# Can rule out UTF-8 if C0-C1 or F5-FF found
	if re.search('[\xc0-\xc1\xf5-\xff]', buf):
		# don't know what it is
		return (None, buf)
		
	# if at least two UTF-8 multibyte sequences found, asssume UTF-8
	if re.search('%s.*%s' % (re_UTF8_mbchar, re_UTF8_mbchar), buf):
		return ('UTF-8', buf)

	# unknown encoding
	return (None, buf)

def wikitext_as_unicode(buf):
	"""
	Given raw wikitext (binary), convert to Unicode using
	the best method.
	"""
	if isinstance(buf, unicode):
		return buf # watch for unicode being passed
		
	enc,buf = detect_encoding(buf)
	if enc is None:
		buf = unicode(buf) # hope the default encoding works!
	else:
		buf = unicode(buf, enc)
		
	return buf
	
def load_wikitext(filename):
	"""
	Load WikklyText from a file, handling encodings if given.
	
	Returns Unicode text from file.
	"""
	buf = open(filename,'rb').read()
	return wikitext_as_unicode(buf)
	
def escape_text_for_html(txt):
	"Escape text so it will appear as-is when placed in HTML"
	# careful on ordering
	txt = txt or ''
	txt = txt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
	txt = txt.replace('\t',' '*4).replace(' ','&nbsp;')
	txt = txt.replace('\n','<br>')

	return txt
	
def bytes_to_str(nr):
	"Convert 'nr' (# bytes) to a nice printable format."
	if nr < 1000:
		return '%d' % nr
	else:
		return '%.1fk' % (nr/1000.0)
		
def ifelse(cond, a, b):
	"returns (cond ? a:b)"
	if cond: return a
	else: return b

def make_etree_map(root):
	"""
	Given an ElementTree node, map some node-to-node relationships.
	
	Returns:
		(parent_map, prevsib_map)
		
	Where:
		parent_map[node] = Parent of node (or None)
		prevsib_map[node] = Previous sibling of node (or None)
	"""
	parent_map = {}
	prevsib_map = {}
	prev = None
	for node in root.getiterator():
		for subnode in node:
			parent_map[subnode] = node
			prevsib_map[subnode] = prev
			prev = subnode

	return (parent_map, prevsib_map)

def HTML_PRE(encoding, title=None, stylesheet='css/wikklytext.css',
		include_navmenu=True):
	"""
	Return a minimal HTML header for WikklyText HTML output.
	The returned header will have an opened <div class='wikkly-content-container'>,
	but no menu or title divs. This is meant as a bare header for standalone
	content, error messages, etc. For custom page layouts, you'll want
	to make your own header.
	
	encoding is an encoding like 'utf-8'.
	title is an optional document title.
	
	Returns encoded string.
	"""
	pre = u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=%s"/>
<link href="%s" rel="stylesheet" type="text/css"/>""" % (encoding, stylesheet)

	# <title> required, even if empty, for XHTML
	pre += '<title>%s</title>' % (title or '')
		
	pre += "</head><body class='wikkly-body'>"
	# add spacer at top
	pre += '<div class="wikkly-top-spacer"></div>'
	# create bare document structure (see wikklytext.css)
	pre += '<div class="wikkly-outside-container">'
	# go ahead and make other empty divs in case 3rd party code is
	# parsing them
	pre += '<div class="wikkly-title-container"></div>'
	if include_navmenu:
		pre += '<div class="wikkly-navmenu-container"></div>'
	# leave content div open
	pre += '<div class="wikkly-content-container">'
	
	return pre.encode(encoding)

def HTML_POST(encoding):
	"""
	Return a standard HTML footer for WikklyText HTML output.
	
	encoding is an encoding like 'utf-8'.
	
	Returns encoded string.
	"""
	# close content-container
	h = u'</div>'
	
	# close outer container
	h += u'</div>'
	
	# add footer div for consistency with wiki layout.py
	h += u'<div class="wikkly-footer-container">'
	h += u'</div>'
	
	# close html
	h += u'</body>'
	h += u'</html>'
	
	return h.encode(encoding)

def Text(text, kind='Text'):
	"Convenience for creating Text* nodes. 'kind' can be Text, TextCode or TextHTML."
	t = Element(kind)
	t.text = text
	return t

def DIV(classname=None, style=None, id=None):
	"""
	Create a block-level element (like an HTML <div>).
	
	'classname' is a CSS class
	'style' is an inline CSS 'style=' string
	'id' is for the 'id=' string
	
	All are optional.
	
	CAUTION: In Safe Mode, DO NOT pass any user-entered text as 'classname', 'style' or 'id'.
	         Any values you pass must be safe, there is no checking done here (to give
			 macros maximum flexibility).
			 (NOTE: buildHTML sanity checks 'classname' and 'id', but in general don't allow
			 arbitrary texts to be placed here.)
			 
	Returns Element
	"""
	div = Element('MacroBlock')
	if classname: # not None or not empty
		div.set('class', classname)
		
	if style:
		div.set('style', style)
		
	if id:
		div.set('id', id)
		
	return div
	
def SPAN(classname=None, style=None, id=None):
	"""
	Like DIV() but creates an inline element (like HTML <span>). See DIV() docs.
	"""
	span = Element('MacroInline')
	if classname: # not None or not empty
		span.set('class', classname)
		
	if style: 
		span.set('style', style)
		
	if id: 
		span.set('id', id)
		
	return span
	
def ElementList():
	return Element('ElementList')

# get path where scripts are stored
import os
path,name = os.path.split(__file__)
if not len(path):
	MYPATH = os.getcwd()
else:
	MYPATH = path

from threading import Lock
LOGDIR = None
LOGDIR_LOCK = Lock()

def enable_logging(val):
	global LOGDIR
	if val:
		newval = os.path.join(MYPATH,'content_log')
	else:
		newval = None

	LOGDIR_LOCK.acquire()
	LOGDIR = newval
	LOGDIR_LOCK.release()
	
def hashtext(utext):
	import md5
	m = md5.new(utext)
	return m.hexdigest()
	
def log_content(utext, html):
	import re
	from time import time
	import gzip
	
	# convert content to UTF-8 for saving
	if not isinstance(utext, unicode):
		raise WikError("Expecting unicode, got '%s'" % repr(utext))
		
	u8text = utext.encode('utf-8')
	
	# did any errors occur?
	if re.search(r'<div class="wikkly-error-body">', html):
		# yes, save as error log
		name = 'error-%s-%.2f.log.gz' % (hashtext(u8text), time())
	else:
		# no error, save as "OK"
		name = 'ok-%s-%.2f.log.gz' % (hashtext(u8text), time())

	LOGDIR_LOCK.acquire()
	if LOGDIR is None:
		LOGDIR_LOCK.release()
		return # user has not requested logging
				
	try:
		if not os.path.exists(LOGDIR):
			os.makedirs(LOGDIR)
			
		full = os.path.join(LOGDIR, name)
		LOGDIR_LOCK.release()
	except:
		# user probably lacks write permission -- ignore and continue
		LOGDIR_LOCK.release()
		return
		
	f = gzip.GzipFile(full, 'wb', 3)
	f.write(u8text)
	f.close()
	
def get_version():
	"Get WikklyText version string."
	import wikklytext.version as version
	return version.VSTR
	
