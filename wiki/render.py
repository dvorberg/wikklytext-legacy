"""
wikklytext.wiki.render.py: Rendering of WikklyText.

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
__all__ = ['render_inner_html']

from wikklytext.store import makeFSname
from wikklytext import WikError, WikklyText_to_InnerHTML
import os, re
from wikklytext.base import ifelse
from urllib import urlencode

class URLResolver(object):
	"""
	Resolves URLs by looking in store to see if names exist.
	If so, points the URL to the rendered HTML file.
	"""
	def __init__(self, wiki):
		"wiki is a WikklyWiki"
		self.wiki = wiki
		
	def makeurl(self, base_url, name, query, fragment):
		"""
		This is the same as what urlparse.urlunsplit does, except
		that it knows 'base_url' should be used as-is, and to 
		add .html to name.
		"""
		url = base_url + name + '.html'
		url += ifelse(query and len(query), '?' + query, '')
		url += ifelse(fragment and len(fragment), '#' + fragment, '')

		return url
		
	def resolver(self, url_fragment, base_url, site_url):
		#print "RESOLVER IN", url_fragment, base_url, site_url
		url,kind = self._resolver(url_fragment, base_url, site_url)
		#print "RESOLVER OUT",url,kind
		return url,kind
		
	def _resolver(self, url_fragment, base_url, site_url):
		from urlparse import urlsplit, urlunsplit
		# I ignore the parsed scheme & netloc and use base_url instead.
		# This avoids confusion with names like "Name: Here"
		# (setting to 'http' does not work -- causes URLs like "http:///.."
		# which don't work ...)
		scheme,netloc,path,query,frag = urlsplit(url_fragment)
		
		#print "RESOLVER IN",repr(scheme),repr(netloc),repr(path),repr(query),repr(frag)
		
		if path[-7:] == 'rss.xml':
			# report as internal URL
			return (base_url + 'rss.xml', 'internal')
		
		# refs to 'files/*' are internal
		if path[:6] == 'files/':
			return (base_url + path, 'internal')
			
		# redirect DefaultTiddlers -> index
		if path == 'DefaultTiddlers':
			path = 'index'
			
		# see if it is a special name that won't exist in the wiki itself (either
		# an index-* file, or a command like DoServerCmd?cmd=...)
		if path in ['index', 'index-Names', 'index-Tags', 'index-Timeline','DoServerCmd']:
			# report it as an internal URL
			url = self.makeurl(base_url, path, query, frag)
			#print "RESOLVER OUT (1)",repr(url)
			return (url, 'internal')
		
		# if path is a tiddler name, return link to rendered file
		item = self.wiki.store().getitem(path)
		if item is None:
			# if that failed, try loading with entire URL (catches things like "Name??")
			item = self.wiki.store().getitem(url_fragment)
			
		if item:
			name = makeFSname(item.name)
			
			# only DoServerCmd is allowed to have a query, so leave query
			# empty here (this allows pages like "Name??" to be linked to).
			url = self.makeurl(base_url, name, '', frag)
			
			#print "RESOLVER OUT (2)",repr(url)
			
			# report it as an internal URL (in a sense, all tiddlers are anchors,
			# so this is logical to do here)
			return (url, 'internal')
		
		# if it looks like a regular URL, let default handler take it (XXX this is
		# copied from the lexer - maybe need to refactor later)
		if re.match(r"((http|https|file|ftp|gopher|mms|news|nntp|telnet)://[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+(:?\:[0-9]+)?(?:[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+)?)|(mailto:[a-zA-Z\._@]+)",
						url_fragment):
			return (None,None)
	
		# if its an anchor, do nothing
		if len(frag):
			return (None,None)
			
		# if its a local pathname, make link
		if os.path.exists(url_fragment):
			return ('file:///%s' % url_fragment, 'external')
			
		# else, make it an auto-item if auto wiki words are enabled
		if self.wiki.get_link_unknown_camelwords():
			p = {'cmd': 'newItem', 'name': url_fragment}
			url = self.makeurl(base_url, 'DoServerCmd', urlencode(p), '')
			return (url, 'newitem')
		else:
			# do default URL resolution
			return (None,None)
		
class PostHook(object):
	def __init__(self, wiki):
		# make map of wikiwords
		self.wiki = wiki
		self.wikiwords = {}
		for name in wiki.store().names():
			self.wikiwords[name] = name

	def on_unknown_camelword(self, word):
		# make links to unknown camelwords?
		if self.wiki.get_link_unknown_camelwords():
			return ('{{a-unknown-item{[[%s|DoServerCmd?cmd=newItem&name=%s]]}}}' % (word,word), True)
		else:
			return (word, False)
		
	def treehook(self, rootnode, context):
		from wikklytext.wikwords import wikiwordify
		# add links to wikiwords
		wikiwordify(rootnode, context, self.wikiwords, self.on_unknown_camelword)

def get_item_skiplist(wiki):
	"""
	Try to find an item 'DoNotRender' and get a list of item
	names to not render.
	"""
	# The skiplist is saved in a item ('DoNotRender') -- the reason
	# it is not a tag (like '-cache') is that you may want to skip
	# .txt files in a 'text' wiki that aren't really items, and so
	# wouldn't have any way to be tagged.
	from wikklytext.store import tags_split
	item = wiki.getitem('DoNotRender')
	if item is None:
		return []
	else:
		return tags_split(item.content)
	
def render_text_inner_html(wiki, text, UID=None, xml_posthook=None):
	"""
	Worker routine to render wiki content.
	
	wiki: WikklyWiki where content originated (used to find inner-wiki links).
	text: Content. Assumes caller has done any needed preprocessing; it is
	      simply rendered as-is into HTML.
	UID: User ID to use for 'safe mode' settings.
	     Can pass None to force safe_mode=False
	xml_posthook: Hook to get generated XML (encoded bytestring). Called as:
				     xml_posthook(xml, context)
	
	Returns: innerHTML, as UTF-8 encoded bytestring
	"""
	import sys
	from time import time
	from boodebr.util import makeSHA
	
	time_entry = time()
	store = wiki.store()
	safe_mode = wiki.user_get_safemode(UID)
	if safe_mode:
		max_runtime = wiki.get_safemode_timelimit()
	else:
		max_runtime = -1
		
	url_resolve = URLResolver(wiki)
	posthook = PostHook(wiki)
	
	# variables to set in WikContext
	setvars = {
		'$FS_CWD': store.getpath(),
		'$BASE_URL': wiki.getRT_baseurl(),
		}
		
	# render to inner HTML
	try:
		html,context = WikklyText_to_InnerHTML(text, 'utf-8', 
						safe_mode,
						setvars,
						url_resolver=url_resolve.resolver,
						tree_posthook=posthook.treehook,
						max_runtime=max_runtime,
						xml_posthook=xml_posthook,
						plugin_dirs=wiki.get_all_plugin_dirs(),
						rendercache=wiki.rendercache(),
						macro_handler=wiki.macro_handler)						
	except WikError:
		from wikklytext.base import HTML_PRE, HTML_POST
		from wikklytext.error import exception_to_html
		html = exception_to_html(sys.exc_info(), HTML_PRE('utf-8'), 
					HTML_POST('utf-8'), 'utf-8')
		
	return html
	
def render_inner_html(wiki, name, UID=None):
	"""
	Render named item from the store and return inner HTML.

	wiki: WikklyWiki holding item
	name: Name of item to load
	UID: User ID to use for 'safe mode' settings.
	     Can pass None to force safe_mode=True

	Returns: (innerHTML [utf-8 bytestring], wikContext)
	"""
	item = wiki.store().getitem(name)
	
	content = u''
	if item.content_type == 'TiddlyWiki':
		# turn off reflow to match TiddlyWiki formatting
		content += u'<<set $REFLOW 0>>\n'
		
	content += item.content
	return render_text_inner_html(wiki, content, UID)
