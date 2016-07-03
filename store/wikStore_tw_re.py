"""
wikStore_tw_re: Implements a read/write store as a TiddlyWiki file.

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
import re, os
from wikStore import WikklyItem, WikklyDateTime
from boodebr.util.locking import open_locked

def VER(major,minor,rev):
	"Make a linear version number for easy comparison."
	return (major*100*100) + (minor*100) + rev
	
def escape_for_tw(txt, to_pre=False):
	"""
	Escape text for placing into TiddlyWiki.
		
	to_pre is True/False if txt is going to be put inside a <pre> storage area.
	"""
	#print "ESCAPING",repr(txt)
		
	# careful on ordering ...
	pairs = [('&','&amp;'), ('<','&lt;'), ('>','&gt;'),
				('"','&quot;'), ('\r','')]
				
	if not to_pre:
		pairs += [('\\','\\s'), ('\n','\\n')]
		
	for a,b in pairs:
		txt = txt.replace(a,b)
	
	#print "ESCAPED TO",repr(txt)
	
	# now escape unicode codepoints -> HTML entities
	txt = escape_html_entities(txt)
	
	return txt

def unescape_from_tw(txt, from_pre=False):
	"""
	Unescape tiddlywiki text.
	
	from_pre is True/False if text comes from a <pre> storage area.
	"""
	# unescape HTML entities first
	txt = unescape_html_dentities(txt)
	
	# careful on ordering ...
	pairs = [('&lt;','<'), ('&gt;','>'), ('&quot;','"'),
				('&amp;','&')]
				
	if not from_pre:
		pairs += [('\\n','\n'), ('\\s', '\\')]
		
	#print "UNESCAPING",repr(txt)
	#print "PAIRS",pairs
	
	for a,b in pairs: 
		txt = txt.replace(a,b)
		
	return txt
	
def escape_html_entities(utxt):
	"""
	Given a unicode string, replace all codepoints that are known HTML
	entities with decimal entities (&#NNNN;). Names are not used since
	TW uses decimal entities as well.
	"""
	from htmlentitydefs import codepoint2name
	
	out = u''
	for c in utxt:
		# careful not to escape chars already handled
		if c not in '&<>"\r\\\n' and codepoint2name.has_key(ord(c)):
			out += '&#%d;' % ord(c)
		else:
			out += c
			
	return out

def unescape_html_dentities(txt):
	"""
	Takes a string with HTML decimal entities like:
		&#NNNN;
		
	... and returns a unicode string with those entities
	converted to unicode.
	"""
	import re
	rh = re.compile('&#([0-9]+);')

	parts = rh.split(txt)
	# parts = [text, entity, text, entity ... text]
	text = 1
	out = u''
	for p in parts:
		if text:
			out += p
			text = 0
		else:
			out += unichr(int(p))
			text = 1
			
	return out

def get_tw_version(buf):
	"""
	Get TiddlyWiki version number from file contents.
		
	Returns linear version number. Use VER() for comparisons.
	'buf' is the unicode text from the TiddlyWiki.
	"""
	m = re.search(r'var version\s*=\s*{(.+?)};', buf)
	if not m:
		raise Exception("ERROR locating version")
	
	txt = m.group(1)
	
	m = re.search(r'major:\s*([0-9]+)', txt)
	major = int(m.group(1))

	m = re.search(r'minor:\s*([0-9]+)', txt)
	minor = int(m.group(1))
	
	m = re.search(r'revision:\s*([0-9]+)', txt)
	rev = int(m.group(1))
	
	return VER(major,minor,rev)

def tw_format_div(item, version):
	"""
	Create a <div> from an item, ready for placement into the storeArea. 
	Returns unicode string.
		
	version = VER() for the version of TiddlyWiki being written.
	"""
	from wikStore import tags_join
		
	if version >= VER(2,2,0):
		div = u'<div title="%s"' % escape_for_tw(item.name)
	else:
		div = u'<div tiddler="%s"' % escape_for_tw(item.name)
		
	div += u' modifier="%s"' % escape_for_tw(item.author)
	
	# TW 2.2.x only saves mtime if != ctime
	if (version >= VER(2,2,0) and item.mtime != item.ctime) or (version < VER(2,2,0)):
		div += u' modified="%s"' % item.mtime.to_store()
		
	div += u' created="%s"' % item.ctime.to_store()
	
	if len(item.tag_list()) or version < VER(2,2,0):
		# TW 2.0.x and 2.1.x always write tags, even if empty
		div += u' tags="%s"' % escape_for_tw(tags_join(item.tag_list()))
		
	if version >= VER(2,2,0) and item.revision is not None:
		div += u' changecount="%s"' % unicode(item.revision)
		
	if version >= VER(2,2,0):
		content = escape_for_tw(item.content, to_pre=True)
		div += '>\n<pre>%s</pre>\n</div>' % content
	else:
		div += '>%s</div>' % escape_for_tw(item.content)
	
	return div

def tw_parse_div_name(div):
	"""
	Get just the tiddler name from div.
		
	div is an item from get_all_divs().
	"""
	m = re.search(r'(tiddler|title)="(.+?)"', div, re.M|re.S)
	if m is None:
		raise Exception("Cannot get div name from: %s" % \
				repr(div[:100]))
		
	return unescape_from_tw(m.group(2))

def tw_parse_div_next_attr(text):
	m = re.match(r'\s*>', text)
	if m:
		return (len(m.group(0)),None,'') # end of tag
		
	m = re.match(r'(.+?)="(.*?)"\s*', text)
	if not m:
		raise Exception("Unable to find next attr at point: %s" % text[:400])
		
	return (len(m.group(0)), m.group(1), m.group(2))

def tw_parse_div_attrs(div):
	attrs = {}
	while 1:
		nr, name, value = tw_parse_div_next_attr(div)
		if name is None:
			return (attrs, div[nr:])
			
		# -- normalize attr names across TW versions --
		
		# (tiddler|title) -> title
		if name == 'tiddler':
			name = 'title'
			
		attrs[name] = value
		div = div[nr:]

def tw_parse_div(div):
	"""
	Parse a <div> into a WikklyItem.
	
	div is an item from get_all_divs().
	"""
	from wikStore import tags_split
	#print "PARSE DIV",div
	
	# skip "<div" portion
	m = re.match(r'\s*<div\s*', div)
	if not m:
		raise Exception("ERROR parsing <div> @ %s" % (div[:400]))
		
	div = div[len(m.group(0)):]
	
	# split tag attributes
	attrs,txt = tw_parse_div_attrs(div)
	
	name = unescape_from_tw(attrs['title'])
	
	# 'modifier' is optional in TW 2.3.x
	author = unescape_from_tw(attrs.get('modifier', u'Unknown'))
	s_ctime = attrs.get('created', '')
	s_mtime = attrs.get('modified', '')
	# watch for either/both missing
	if len(s_ctime) and len(s_mtime):
		ctime = WikklyDateTime(from_store=s_ctime)
		mtime = WikklyDateTime(from_store=s_mtime)
	elif len(s_ctime) and not len(s_mtime):
		# 'modified' is optional in TW 2.2.x - use ctime
		ctime = WikklyDateTime(from_store=s_ctime)
		mtime = WikklyDateTime(from_store=s_ctime)
	elif not len(s_ctime) and len(s_mtime):
		# only ctime missing -- use mtime
		ctime = WikklyDateTime(from_store=s_mtime)
		mtime = WikklyDateTime(from_store=s_mtime)
	else:
		# both missing, use localtime
		ctime = WikklyDateTime()
		ctime.from_localtime()
		mtime = WikklyDateTime()
		mtime.from_localtime()
		
	tags = attrs.get('tags', u'')
	tags = tags_split(unescape_from_tw(tags))
	revision = attrs.get('changecount', None)
	if revision is not None:
		revision = int(revision)
	
	#print "MATCH ON",div[m.start(0):m.end(0)]
	#print "GROUPS",m.groups()
	#print "AUTHOR",author
	#print "MTIME",mtime
	#print "CTIME",ctime
	#print "TAGS",tags
	
	# remainder is content - careful here ...
	m = re.match(r'\s*<pre>(.*)</pre>',txt,re.M|re.S)
	if m:
		content = unescape_from_tw(m.group(1), from_pre=True)
	else:
		content = unescape_from_tw(txt)
	
	#print "UNESCAPED CONTENT",repr(content)

	return WikklyItem(name, content, tags, author, ctime, mtime, 
				u'TiddlyWiki', revision)
	
def tw_split_wiki(buf):
	"""
	Given the entire contents of a  TiddlyWiki, return:
		(start, store, end)
		
	Where the TiddlyWiki can be reassembled as:
		wiki = start + store + end
		
	NOTE:
		'store' is PURELY the content <divs>. The "storeArea" wrapper is
		part of start & end.
	"""
	m = re.match(r'(.+<div id="storeArea">\s*)((<div.+?>.+?</div>[\n]?)*)(\s*</div>.+)', buf, re.M|re.S)
	if not m:
		raise Exception("Cannot split wiki.")
	
	#print "Split END",repr(m.group(4)[:80])
	return (m.group(1), m.group(2), m.group(4))

def detect(pathname):
	"""
	Detect if the given pathname is a TiddlyWiki file.
	(pathname can be a file or directory name.)
	
	Returns a wikStore_tw_re instance if so, or None if not.
	"""
	w = wikStore_tw_re(pathname)
	# do NOT detect by counting tiddlers since it might be empty.
	# get version instead and catch error if not a TW file.
	try:
		w.twversion()
		return w
	except:
		return None
		
class wikStore_tw_handler(object):
	def __init__(self, filename, version="2.4"):
		"""
		Object that handles the lowlevel read/write access to a TiddlyWiki.
		
		filename: Name (full path) of TiddlyWiki HTML file.
		
		If filename doesn't exist, 'version' specifies which
		template to use to create the new TiddlyWiki. (If filename
		exists, 'version' is not used -- there is no conversion
		performed if the file is an older version.)
		
		** NOTE **
		
		The TiddlyWiki file is locked the *entire time* this object exists,
		so you should create a handler, do your operation, then unlock() before
		deleting it.
		
		Recommended usage:
			try:
				handler = wikStore_tw_handler(...)
				result = handler.op()
			finally:
				handler.unlock() # don't count on auto-deletion
		"""
		import wikklytext.base
		from pkg_resources import resource_string
	
		self.filename = os.path.abspath(filename)
		if os.path.isdir(filename):
			raise Exception("filename cannot be a directory")
		
		# open and lock file
		self.locked_file = open_locked(filename, timeout=20)
		# new file?
		b = self.locked_file.read(1)
		self.locked_file.seek(0)
		if len(b) == 0:
			# create blank from template
			name = 'BlankTiddlyWiki-%s.htm' % version
			blank = resource_string('wikklytext.store', 'templates/%s' % name)
			self.locked_file.write(blank)
			self.locked_file.seek(0)
			
		self.locked_buf = unicode(self.locked_file.read(), 'utf-8', 'replace')
		
	def __del__(self):
		if self.locked_file is not None:
			self.unlock()
			
	def unlock(self):
		"""
		Better to call this when finished with handler than to rely on object
		going out of scope and being auto-deleted.
		"""
		self.locked_file.close()
		# catch it being used again
		self.locked_file = None
		self.locked_buf = None 
		
	def info(self):
		"Return a one-line description of this instance."
		return 'TiddlyWiki %s' % self.filename
	
	def names(self):
		"""
		Return names of all content items in store as a list of unicode strings.
		"""
		return [tw_parse_div_name(div) for div in self.get_all_divs()]
		
	def getitem(self, name):
		"Load a single item. Returns WikklyItem, or None if not found."
		for div in self.get_all_divs():
			if tw_parse_div_name(div) == name:
				return tw_parse_div(div)
				
		return None # not found
		
	def getall(self):
		"Return all items in store as a list of WikklyItems"
		return [tw_parse_div(div) for div in self.get_all_divs()]
	
	def saveitem(self, item, oldname=None, do_delete=False):
		"""
		Save a WikklyItem to the store.
		
		If oldname != None, passed item replaces the item of the given name.
		Notes:
			* Passing oldname=None is the way to store a new item, or
			  overwrite an existing item.
			* Passing oldname=item.name is the same as passing oldname=None
		
		Tries to replicate the formatting of TiddlyWiki but note:
		    1. There may be some minor whitespace differences, not affecting content.
			2. This code escapes HTML entities more aggressively than TiddlyWiki, 
			   but produces an equivalent HTML stream.
			   
		Implementation note: regex.sub() is not used to write content -- between HTML 
		escaping and regex escaping this becomes complex and error prone. I prefer
		the structured approach below.
		
		** do_delete is for internal use only **
		"""		
		if oldname == item.name:
			oldname = None # make sure no side effects below .. this is what user meant to do
			
		version = self.twversion()
		
		start,store,end = self.split_wiki(self.locked_buf)
		
		#newstore = u'<div id="storeArea">'
		#if version >= VER(2,1,0):
		#	newstore += u'\n'
		newstore = u''
		
		wrote_item = False
		
		for div in self.get_all_divs():
			name = tw_parse_div_name(div)
			if name == oldname or (do_delete and name == item.name):
				continue # rename or delete
				
			if name == item.name:
				if not do_delete:
					# overwrite at same location in store
					newstore += tw_format_div(item, version) + '\n'
					wrote_item = True
			else:
				# save as-is including formatting
				newstore += div.lstrip() + u'</div>' + '\n'
				
		if not wrote_item and not do_delete:
			# add new item at end
			newstore += tw_format_div(item, version) + '\n'
			
		#newstore += '</div>'
		
		# implementation note: '\r' chars are removed at the caching level.
		
		self.locked_buf = (start + newstore + end)
		self.locked_file.truncate(0)
		self.locked_file.seek(0)
		self.locked_file.write(self.locked_buf.encode('utf-8'))
		
	def delete(self, item):
		"""
		Delete the given WikklyItem from the store.
		"""
		self.saveitem(item, do_delete=True)
		
	def search(self, query):
		"""
		Return a list of items matching query.
		
		'query' is one of the WikklyQuery* objects defined 
		in wikklytext.store.query.
		"""
		from wikklytext.store.wikQuery import generic_query_store
		return generic_query_store(self, query)

	# -- INTERNAL API --
	def twversion(self):
		"""
		Get TiddlyWiki version number from file.
		
		Returns linear version number. Use VER() for comparisons.
		"""
		return get_tw_version(self.locked_buf)
		
	def split_wiki(self, buf):
		"""
		Given the entire contents of a  TiddlyWiki, return:
			(start, store, end)
			
		Where the TiddlyWiki can be reassembled as:
			wiki = start + store + end
			
		NOTE:
			'store' is PURELY the content <divs>. The "storeArea" wrapper is
			part of start & end.
		"""
		return tw_split_wiki(buf)
		
	def get_store(self):
		"""
		Get block of text from tiddlywiki file:
			<div id="storeArea">
				... storage divs ...
			</div>
		
		Returns the "... storage divs ..." text as unicode.
		"""
		start,store,end = self.split_wiki(self.locked_buf)
		return store
		
	def get_all_divs(self):
		"""
		Get all <divs> from storeArea as a list of
		unicode strings:
			<div ...>CONTENT
			
		(Note that there is no final </div> on the strings!) 
		"""
		return self.get_store().split('</div>')[:-1]
		
if __name__ == '__main__':
	import sys		
	from time import time
	
	t1 = time()
	w = wikStore_tw_re(sys.argv[1])
	names = w.names()
	dt = time()-t1
	
	print "Scanned %d names in %.3f secs" % (len(names), dt)
	
	items = w.getall()
	
	dt = time()-t1
	
	print "Got %d items in %.3f secs" % (len(items), dt)
	names2 = [item.name for item in items]
	for name in names2:
		if name not in names:
			print "NOT:",name
			
	buf = w.get_store()
	t1 = time()
	l = buf.split('</div>')[:-1]
	dt = time()-t1
	print "SPLIT INTO %d pieces in %.3f secs" % (len(l),dt)
	#print "0",repr(l[0])
	#print "-1",repr(l[-1])
	
	print "VERSION",w.twversion()
	
	import shutil
	shutil.copy(sys.argv[1], 'aaa.out')
	
	w = wikStore_tw_re('aaa.out')
	
	t1 = time()
	w.saveitem(items[0], None)
	dt = time()-t1
	print "Wrote 1st item in %.3f secs" % dt
	
	# inefficient, but I want to overwrite all items to show
	# that the resulting wiki is equivalent to the original
	t1 = time()
	for item in items:
		w.saveitem(item, None)
		
	dt = time()-t1
	print "Wrote %d items in %.3f secs" % (len(items),dt)

