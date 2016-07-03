"""
wikklytext.wiki.web: Provide access to wiki in a RESTful sort of way. Mounted under /api.

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

"""
URIs:
	
/
	Root of API (externally visible as '$SITE/api')
/pages/NAME
	Rendered page for the given item name
/plugins
	Show info on installed plugins
/plugins/NAME/*
	URLs served by plugin
"""

import wikklytext.wiki.layout as layout
import re
from wsgifront import dispatch, request_uri, shift_path_info
from wikklytext.wiki.util import content_type_for_xhtml
from boodebr.ion import deionize

def default(environ, start_response):
	wiki = environ['wsgifront.x-wikklytext-wiki']
	UID = environ['wsgifront.x-wikklytext-UID']
				
	status = '404 Not Found'
	headers = [('Content-type', 'text/plain')]
	
	start_response(status, headers)
	
	return ['Bad URL: %s' % request_uri(environ)]
	
def pages(environ, start_response):
	"/pages/NAME"
	wiki = environ['wsgifront.x-wikklytext-wiki']
	UID = environ['wsgifront.x-wikklytext-UID']
			
	# PATH_INFO = '/NAME'
	name = environ['PATH_INFO']
	if name[0] == '/':
		name = name[1:]
		
	item = wiki.getitem(name)
	if item is None:
		status = '404 Not Found'
		headers = [('Content-type', 'text/plain')]
	
		start_response(status, headers)
	
		return ['No such item %s' % name]

	else:
		status = '200 OK'
		headers = [('Content-type', 'text/html')]
	
		start_response(status, headers)
	
		return [layout.layoutPage(wiki, item, UID)]
		
def handle_plugins(environ, start_response):
	"/plugins"
	from wikklytext.plugins import load_plugins
	from wikklytext.wiki.render import render_text_inner_html
	from wikklytext.wiki.layout import HEAD
	from copy import copy
	from wsgifront import shift_path_info, dispatch
	import os
	
	wiki = environ['wsgifront.x-wikklytext-wiki']
	UID = environ['wsgifront.x-wikklytext-UID']
		
	plugins = wiki.load_plugins()
		
	if (len(environ['PATH_INFO']) == 0 or environ['PATH_INFO'] == '/'):
		
		modules = dict(plugins.modules)
		names = modules.keys()
		names.sort()
		
		h = ''
		
		h += '!!Plugins\n'
		
		h += '\nThere are %d plugins currently loaded.\n' % len(modules)
		
		h += '* [[Package Info|#PKGINFO]]\n'
		h += '* [[Safe Macros|#SAFE_MACROS]]\n'
		h += '* [[Unsafe Macros|#UNSAFE_MACROS]]\n'
		h += '* [[Embedded Functions|#EMBED_FUNCS]]\n'
		h += '* [[WSGI Macros|#WSGI_MACROS]]\n'
		h += '* [[WSGI Apps|#WSGI_APPS]]\n'
		h += '* [[CSS Definitions|#CSS]]\n'
		
		h += '[[#PKGINFO]]\n'
		for name in names:
			h += '!!!plugin: %s\n' % name
			#h += '%s\n' % modules[name].__file__
			p,n = os.path.split(modules[name].__file__)
			if not len(p):
				p = os.getcwd()
				
			mf = os.path.join(p, 'METADATA')
			if not os.path.isfile(mf):
				h += '* //No metadata//\n'
				continue
				
			try:
				meta = deionize(open(mf, 'rb').read())
			except:
				h += '* @@Bad metadata@@\n'
				continue
				
			h += "* //Name//: %s\n" % meta['name']
			h += '* //Description//: %s\n' % meta['description']
			h += '* //Author//: <nowiki>%s</nowiki>\n' % meta['author']
			h += '* //Version//: %s\n' % meta['version']
			h += '* //URL//: [[%s]]\n' % meta['url']
			
		h += '!!![[#SAFE_MACROS]]Safe macros (//usable by all//)\n'
		
		names = plugins.safe.keys()
		names.sort()
		for name in names:
			func = plugins.safe[name]
			h += ';%s\n' % name
			h += ":''From'' %s\n" % (func.__module__)
			h += func.__doc__ or ''
			
		h += '!!![[#UNSAFE_MACROS]]Unsafe macros (//for trusted users only//)\n'
		names = plugins.unsafe.keys()
		names.sort()
		for name in names:
			func = plugins.unsafe[name]
			h += ';%s\n' % name
			h += ":''From'' %s\n" % (func.__module__)
			h += func.__doc__ or ''
			
		h += '!!![[#EMBED_FUNCS]]Embedded functions\n'
		names = plugins.embed.keys()
		names.sort()
		for name in names:
			func = plugins.embed[name]
			h += ';%s\n' % name
			h += ":''From'' %s<br>\n" % (func.__module__)
		
		h += '!!![[#WSGI_MACROS]]WSGI macros (//usable by all//)\n'
		
		names = plugins.wsgi_macros.keys()
		names.sort()
		for name in names:
			func = plugins.wsgi_macros[name]
			h += ';%s\n' % name
			h += ":''From'' %s\n" % (func.__module__)
			h += func.__doc__ or ''
			
		h += '!!![[#WSGI_APPS]]WSGI Applications (under /api/plugins)\n'
		urls = plugins.wsgi_apps.keys()
		urls.sort()
		for url in urls:
			func = plugins.wsgi_apps[url]
			h += ';%s\n' % url
			h += ":''From'' %s\n" % (func.__module__)
			h += func.__doc__ or ''
			
		h += '!!![[#CSS]]CSS added to <HEAD>\n'
		h += '{{{\n%s}}}\n\n' % plugins.css
	
		h = HEAD(baseurl=wiki.getRT_baseurl(), reqheaders=wiki.getRT_wsgienv(),
					styletext=plugins.css) + \
				'<body>' + \
				render_text_inner_html(wiki, h, UID) + \
				'</body></html>'
		
		status = '200 OK'
		# careful on setting proper media type
		headers = [('Content-type', content_type_for_xhtml(environ))]
		
		start_response(status, headers)
		return [h]
	else:
		#h = 'serve %s' % environ['PATH_INFO']
		#status = '200 OK'
		# W3C specifies this media type for XHTML in an XML container
		#headers = [('Content-type', 'text/plain')]
		
		#start_response(status, headers)
		#return [h]
		try:
			return dispatch(plugins.wsgi_apps, environ, start_response)
		except:
			status = '200 OK'
			headers = [('Content-type', 'text/plain')]
		
			h = 'Unable to dispatch %s' % environ['PATH_INFO']
			
			start_response(status, headers)
			return [h]
		
mappings = {
	'/': default, # catch-all
	'/pages': pages,
	'/plugins': handle_plugins,
	}

def rootapp(environ, start_response):
	return dispatch(mappings, environ, start_response)

