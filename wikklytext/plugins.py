"""
/%
wikklytext.plugins: Loading of plugins for WikklyText

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
%/
<<set Element "[[Element|http://effbot.org/zone/pythondoc-elementtree-ElementTree.htm#elementtree.ElementTree._ElementInterface-class]]">>
!!!~WikklyText Plugins

The Plugin API allows you to extend the functionality of ~WikklyText in several ways:
	* You can add new macros than can be called from wikitexts as {{{<<mymacro ..>>}}} ([[link|#CREATE]])
	* You can add functions that appear in the namespace of {{{<?py}}} code embedded in wikitexts. ([[link|#EMBED]])
	* You can attach extra styling information (CSS) to the rendered document ([[link|#STYLE]])

Click a link for more, or read on for full details.

!!![[#CREATE]]Creating new macros

Macros are ordinary Python functions with the following calling sequence: {{{
def mymacro(context, ...):
	...
}}}

Where {{{context}}} is a {{tt{~WikContext}}} (//ref: ''wikklytext.base''//) and the remainder
of the args are passed from the macro call. For example: {{{
<<mymacro 123 456 "abc">>
}}}

Would call: {{{
def mymacro(context, a, b, c):
	# a.text = "123"
	# b.text = "456"
	# c.text = "abc"
}}}

Note that each passed argument is an <<get Element>> so you use {{{.text}}} to get the text portion.
(//More general macros might want to deal with arbitrary [[ElementTrees|http://effbot.org/zone/pythondoc-elementtree-ElementTree.htm#elementtree.ElementTree.ElementTree-class]]
as arguments, but text args are the simplest and most common.//)

Macros can return any of the following:
	* An <<get Element>>
	* A unicode string
	* A byte-string
	* A list/tuple of any of the above types.

Here is what a typical plugin looks like. Let's assume:
	* My plugin is named ''myplugin''. 
	* I'm defining two macros that are safe for anyone to call named ''happy'' and ''nice''. 
	* I'm defining two macros that only trusted users are allowed to call named ''evil'' and ''bad''.
	
My {{{__init__.py}}} would look like this:
	<<codebox "{{{plugins/myplugin/__init__.py}}}" '''
__safe__ = ['happy', 'nice']
__unsafe = ['evil', 'bad']

def happy(context, ...):
	...
	
def nice(context, ...):
	...

.. etc. ..
'''>>

(//In a real plugin, you'd probably split your code up into multiple files. The above
example shows all code being placed in {{{__init__.py}}} for simplicity.//)

!!![[#EMBED]]Creating embedded functions

Embedded functions are ordinary Python functions that are available by default in the
global namespace of embedded Python code ({{{<?py}}}). They //do not// get a {{{context}}}
arg, and are called like any other function (and may return any value).

To add functions to the embedded namespace, add their names to the {{{__embed__}}} list
at the top of your module (similar to {{{__safe__}}} and {{{__unsafe___}}} above).

!!![[#STYLE]]Adding styling (CSS) information

You might find yourself defining new CSS classes as part of your macros. While it is
certainly possible to tell your macro users to add your new styles to their wiki ''~StyleSheet'',
it is much more convenient to provide the classes automatically.

To do this, simply define a module level variable {{{__css__}}} that is a string with
the styling information to be added to the document ''<HEAD>''. For example: 
{{{
__css__ = '''
	div.myclass1 {
		color: red;
	}
	'''
}}}

The string will be added to a ''<style>'' tag when creating the HTML document.

!!!A simple example

Here is a simple complete example:
	
# First, create a folder ''hello'' under ''plugins/'' in your wiki folder.
# Create a file {{{plugins/hello/__init__.py}}} {{{
'''
This is just like any other Python package where you have __init__.py
defining the interface.

__init__ may define any/all/none of: __embed__, __safe__ and __unsafe__.
'''
__embed__ = ['hello_embedded']
__safe__ = ['hello_safe', 'hello_box']
__unsafe__ = ['hello_unsafe']
__css__ = '''
	div.hellobox {
		background: yellow;
		color: black;
		border: 3px solid blue;
		padding-left: 3em;
		}'''
		
'''
For real code you'd probably split these functions into their
own files and just import them here.
'''
def hello_safe(context, msg):
	return "Hello safe, message=%s" % msg.text

def hello_unsafe(context, msg):
	return "Hello unsafe, message=%s" % msg.text

def hello_box(context, msg):
	"A slightly more complex example ..."
	from wikklytext.plugapi import DIV, Text, eval_wiki_text

	d = DIV('hellobox')
	d.append(eval_wiki_text(context, msg.text))
	return d
	
def hello_embedded(msg):
	return "Hello Embedded, message=%s" % msg.text
}}}
# Finally, create a new wiki item with this text: {{{
<?py
def hello(context, msg):
   return hello_embedded(msg) # auto-added to embedded namespace
?> 

/% Minimal example, showing how args are passed. %/
!!!From ''<$py''
<<hello "Embedded message!">>

!!!From ''<nowiki><<hello_safe>></nowiki>''
<<hello_safe "Safe message!">>

!!!From ''<nowiki><<hello_unsafe>></nowiki>''
<<hello_unsafe "Unsafe message!">>

!!!From ''<nowiki><<hello_box>></nowiki>''

<<hello_box '''This text should be inside a yellow box. 
This macro uses a custom CSS class. All
__wikitext__ //styling// @@markup@@ works
here as well.'''>>
}}}

Save the item and you should see that it works.
"""

import os
import new

__all__ = ['load_plugins', 'WikPlugins']

class WikPlugins(object):
	"""
	Returned from [[load_plugins()|#FUNC_load_plugins]]. All currently loaded plugins.
	
	//Attributes://
		;safe,unsafe
			:Dicts of ''{name: func}'' where name can be used as {{{<<name ...>>}}}. \
			 Mapped from {{{__safe__}}} and {{{__unsafe__}}} attrs defined in modules.
		;embed
			:Dict of ''{name: func}'' where name will be inserted into the embedded \
			 namespace for {{{<?py}}} code in wikitexts. Loaded from {{{__embed__}}} attr defined \
			 in module.
		;css
			:CSS styles to be added to ''<HEAD>'' (text).
		;wsgi_apps
			:Dict of WSGI applications defined by plugins, as: {{{URL: handler}}}. \
			Each URL is of form {{{/api/plugins/NAME/SUBURL}}} where NAME is the name \
			of the plugin and SUBURL is the URL path the plugin defined.
		;wsgi_macros
			:Like safe and unsafe, a map of {name: func}. wsgi_macros are just like \
			safe & unsafe macros, except that they receive a WSGI-like environment instead of a \
			WikContext as their first argument.
		;modules
			:List of (name, module) for all loaded plugins. (For information purposes - all \
			functional data has been pulled out and organized in the other attributes here.)
	"""
	def __init__(self, safe, unsafe, embed, css, wsgi_apps, wsgi_macros, modules):
		self.safe = safe
		self.unsafe = unsafe
		self.embed = embed
		self.css = css
		self.wsgi_apps = wsgi_apps
		self.wsgi_macros = wsgi_macros
		self.modules = modules
		
	__init__.no_pydocs = True
	
	def __str__(self):
		s = 'WikPlugins:\n'
		s += '  safe: %s\n' % str(self.safe)
		return s
	
	__str__.no_pydocs = True
		
def load_plugin_modules(plugdir, namespace='plugins'):	
	"""
	Returns a list of (name, module) where name is from "plugins/name".
	"""
	from imp import find_module, load_module
	#ofile,filename,desc = find_module('plugins')
	#plugins = load_module('plugins', ofile, filename, desc)
	#del ofile
	#print "PLUGINS",plugins.__path__

	plist = []
	for name in os.listdir(plugdir):
		#print "TRY LOAD",name
		full = os.path.join(plugdir, name)
		if not os.path.isdir(full):
			continue
			
		#print 'PLUGIN',name
		#ofile,filename,desc = find_module(name, plugins.__path__)
		try:
			fh,filename,desc = find_module(name, [plugdir])
		except ImportError, exc:
			#print "ERROR1",str(exc)
			continue # normal directory - not a module
			
		#print fh,filename,desc
		
		# try..finally form compat with py2.3
		try:
			try:
				p = load_module('%s.%s' % (namespace,name), fh, filename, desc)
				#print "MOD",p
				plist.append((name, p))
			except ImportError,exc:
				# some sort of error loading module, skip and continue
				# XXX probably should report this so user knows why their
				# plugin(s) didn't load
				#print "ERROR2",str(exc)
				pass
		finally:
			if fh:
				fh.close()
			
	#print "RET",plist
	return plist

def valid_callables(module, namelist):
	"Given a list of names, return those that are valid callables as a map of {name: func}"
	funcs = {}
	for name in namelist:
		f = getattr(module, name, None)
		if f is not None and hasattr(f, '__call__'):
			funcs[name] = f
			
	return funcs

def real_load_plugins(plugdirs=None, namespace='plugins'):
	"""
	Load plugins by attempting to import all modules under the given
	directories. For example, given the following directory structure: {{{
	mydirA/
			aaa/
			bbb/
	mydirB/
			ccc/
			ddd/
	}}}
	Passing {{{plugdirs=['mydirA', 'mydirB']}}} will 
	attempt to import modules ''aaa'', ''bbb'', ''ccc'', and ''ddd''.

	Special cases:
		* if {{tt{plugdirs}}} is a string instead of a list, it will be treated as a single directory name
		* {{tt{plugdirs}}} can (currently) be None, meaning to only load the builtin \
		plugins. There is a chance this will change in the future if the \
		builtin macros are made into regular plugins (in which case, plugdir \
		would be required to get __any__ plugins at all).
		
	Returns [[WikPlugins|#CLASS_WikPlugins]]
	"""
	#print "LOAD PLUGINS",plugdirs
	
	# add builtin plugins first, so user plugins can override them
	from boodebr.util import load_module as my_load_module
	mods = [('core', my_load_module('wikklytext.coremacros'))]
	
	# load user plugins
	if plugdirs is not None:
		if isinstance(plugdirs, (str,unicode)):
			plugdirs = [plugdirs] # allow plugdirs to be a single string
			
		assert(isinstance(plugdirs, (list,tuple))) # sanity
		
		for path in plugdirs:
			if os.path.isdir(path): # skip nonexistant paths (might be temporarily unavailable)
				mods += load_plugin_modules(path)

	# go through plugins and pull out interface items
	safe = {}
	unsafe = {}
	embed = {}
	css = ''
	wsgi_apps = {}
	wsgi_macros = {}
	for name, mod in mods:
		safe.update(valid_callables(mod, getattr(mod, '__safe__', [])))
		unsafe.update(valid_callables(mod, getattr(mod, '__unsafe__', [])))
		embed.update(valid_callables(mod, getattr(mod, '__embed__', [])))
		
		css += getattr(mod, '__css__', '') + '\n'
		
		for url, handler in getattr(mod, '__wsgi_apps__', {}).items():
			wsgi_apps['/%s%s' % (name, url)] = handler
		
		wsgi_macros.update(valid_callables(mod, getattr(mod, '__wsgi_macros__', [])))
		
	plugins = WikPlugins(safe, unsafe, embed, css, wsgi_apps, wsgi_macros, mods)
	#print plugins
	return plugins

def load_plugins(plugdirs=None, namespace='plugins'):
	"""
	A little wrapper around real_load_plugins() that catches import
	errors -- namely errors due to being unable to import 'imp'. Was
	initially created to workaround the lack of the imp module under
	GoogleAppEngine.
	
	XXX TODO - make loading of plugins work under GAE, etc., instead of
	just returning an empty set of plugins.
	"""
	try:
		return real_load_plugins(plugdirs, namespace)
	except ImportError:
		# return empty set of plugins
		return WikPlugins({},{},{},'',{},{},[])
		
#embed, safe, unsafe = load_plugins(None)

#print "EMBED",embed
#print "SAFE",safe
#print "UNSAFE",unsafe

