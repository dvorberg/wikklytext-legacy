"""
wikklytext.wiki.core: Core wiki functionality.

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

from boodebr.config import *
import os, sys
from wikklytext.store import WikklyItem, makeFSname
from boodebr.util import makeSHA
from wikklytext.port import *
import threading

def nopfunc(*args, **kwargs):
	pass

# root directory for config files (subdir of wiki path)
WIKIROOT = '.wik'

# wiki settings are stored here (relative to WIKIROOT)
CONFNAME = 'conf'
ROOTKEY = 'WikklyWikiConfig'

# cache of rendered texts is stored in the subdir
RENDERCACHE = 'rendercache'

# valid users are stored here (relative to WIKIROOT)
USERDB = 'users'
USERDBKEY = 'WikiUsers'

class TextExtractor(object):
	def __init__(self):
		self.texts = []
		
	def xmlpost(self, xml, context):		
		from wikklytext import loadxml
		#print "XMLPOST",xml,context,self.texts
		root = loadxml(xml)
		for node in root.getiterator():
			if node.tag in ['Text']:
				self.texts.append(node.text.lstrip().rstrip())
				
# convenience functions for special items
def SiteTitle(wiki):
	"Get SiteTitle as rendered HTML"
	from wikklytext.wiki.render import render_text_inner_html
	from wikklytext.wiki.util import itemText
	return render_text_inner_html(wiki, itemText(wiki, u'SiteTitle', u'No SiteTitle Defined'))
	
def SiteTitleText(wiki):
	"Get just the plaintext portion of SiteTitle"
	from wikklytext.wiki.render import render_text_inner_html
	from wikklytext.wiki.util import itemText
	te = TextExtractor()
	render_text_inner_html(wiki, itemText(wiki, u'SiteTitle', u'No SiteTitle Defined'),
				xml_posthook=te.xmlpost)
	return ' '.join(te.texts)

def SiteSubtitle(wiki):
	"Get SiteSubtitle as rendered HTML"
	from wikklytext.wiki.render import render_text_inner_html
	from wikklytext.wiki.util import itemText
	return render_text_inner_html(wiki, itemText(wiki, u'SiteSubtitle', u'No SiteSubtitle Defined'))
	
def SiteSubtitleText(wiki):
	"Get just the plaintext portion of SiteSubtitle"
	from wikklytext.wiki.render import render_text_inner_html
	from wikklytext.wiki.util import itemText
	te = TextExtractor()
	render_text_inner_html(wiki, itemText(wiki, u'SiteSubtitle', u'No SiteSubtitle Defined'),
				xml_posthook=te.xmlpost)
	return ' '.join(te.texts)

from wikklytext.cache import NullCache, RamCache, FileCacheSerialize

class WikklyWiki(object):
	def __init__(self, path):
		self.path = path
		
		# These do NOT automatically create file, so can go ahead
		# and create them here but not use till I'm sure I should
		self.cfg = configfile(os.path.join(path,WIKIROOT,CONFNAME))
		self.userdb = configfile(os.path.join(path,WIKIROOT,USERDB))
		
		# create ._rendercache
		self._rendercache = None
		
		# choose a cache ... (make selectable later)
		#self._rendercache = NullCache()
		#self._rendercache = RamCache()
		#self._rendercache = FileCacheSerialize(os.path.join(self.confdir(),RENDERCACHE))
		
		# multiple threads might use wiki so store per-request data here
		self.RT = threading.local()
		
	def update_rendercache(self):
		if self.get_cache_flag():
			self._rendercache = FileCacheSerialize(os.path.join(self.confdir(),RENDERCACHE))
		else:
			# XXX make this user-selectable later
			#self._rendercache = NullCache()
			self._rendercache = RamCache()
		
		self._rendercache.set_expire_time(self.get_cache_expire_time())
		self._rendercache.set_clean_interval(self.get_cache_clean_interval())
		
	def get_path(self):
		return self.path
		
	def get_css_path(self):
		"Where are my CSS files stored?"
		return os.path.join(self.get_path(), 'css')

	def metadata_dbname(self):
		return os.path.join(self.confdir(), 'wikidata.db')

	def fpath(self, name):
		return os.path.join(self.get_path(), name)
		
	#-----------------------------------------------------------------
	# The setRT/getRT are for setting/getting values that are set
	# on per-request basis.
	#
	# Uses threading.local in case wiki is shared between threads.
	#-----------------------------------------------------------------
	def setRT_baseurl(self, url):
		"""
		Inform wiki of its base URL in the runtime environment.
		
		For example, if 'index.html' of the wiki is served as:
			http://MYSITE.COM/MY/PATH/index.html
			
		Then set baseurl='http://MYSITE.COM/MY/PATH'.
		
		This value is *NOT* saved permanently, it is set on every request.
		"""
		self.RT.wikklytext_baseurl = url
		
	def getRT_baseurl(self):
		return getattr(self.RT,'wikklytext_baseurl','')
		
	def setRT_wsgienv(self, env):
		"""
		Inform wiki of incoming WSGI environment.
		
		The body will be preread. When retrieving later, a copy of the body will be used so
		you can get the WSGI environment and read it multiple times.
		"""
		from wsgifront import read_body
		
		self.RT.wsgi_env = env
		self.RT.wsgi_body = read_body(env)
				
	def getRT_wsgienv(self):
		"""
		Returns normalized WSGI environment:
			* wsgi.input will hold a copy of the body so multiple callers
			  can get & read the environment safely
			
			* wsgi.errors will be a fake stream -- writing to it has no effect on server
			
		Returns a copy that the caller can freely change.
		"""
		from wsgifront import normheaders
		from wikklytext.base import StringIO
		
		env = normheaders(self.RT.wsgi_env,
				frontname='wikklytext-wiki',
				# each caller sees full body
				f_input=StringIO(self.RT.wsgi_body),
				# ignore error stream
				f_errors=StringIO())
		
		return env
				
	def setRT_curUID(self, uid):
		self.RT.wikklytext_curUID = uid
		
	def getRT_curUID(self):
		return getattr(self.RT, 'wikklytext_curUID', None)
		
	def get_plugin_path(self):
		"""
		Get location of my 'plugins/' or None if it does not exist.
		(Returns *only* my 'plugins/', not any additional user directories.)
		"""
		path = os.path.join(self.get_path(), 'plugins')
		if os.path.isdir(path):
			return path
		else:
			return None
		
	def get_all_plugin_dirs(self):
		"Get list of all paths to search for plugins (my /plugins + user paths)"
		# my /plugins
		path = self.get_plugin_path()
		if path is None:
			paths = []
		else:
			paths = [path]
			
		# add user plugin dirs
		paths += self.get_user_plugin_dirs()
		
		return paths
		
	def load_plugins(self):
		"Load my plugins"
		import wikklytext.plugins
		return wikklytext.plugins.load_plugins(self.get_all_plugin_dirs())
		
	#--------------------------------------------------------------
	# User-defined settings (in CONFNAME)
	#--------------------------------------------------------------
	def initted(self):
		"Has the wiki been initted?"
		return os.path.isfile(os.path.join(self.get_path(),WIKIROOT,CONFNAME))

	def confdir(self):
		return self.fpath(WIKIROOT)
		
	def do_init(self):
		"Create my directory structure."
		if not os.path.isdir(self.confdir()):
			os.makedirs(self.confdir())
			
	def set_kind(self, kind):
		"One of {text, tiddlywiki, sqlite}."
		assert(kind in ('text','tiddlywiki','sqlite'))
		self.cfg.set_str(ROOTKEY, 'kind', kind)

	def get_kind(self):
		return self.cfg.get_str(ROOTKEY, 'kind', None)
	
	def set_filename(self, name):
		"""
		For kind={tiddlywiki|sqlite}, the filename to use for storage.
		This sets the basename only, in case you are running from
		another location.
		"""
		self.cfg.set_str(ROOTKEY, 'filename', os.path.basename(name))

	def get_filename(self):
		"""
		For kind={tiddlywiki|sqlite}, the filename to use for storage.
		Returns the full path, in case you are running from another location.
		"""
		name = self.cfg.get_str(ROOTKEY, 'filename', None)
		if name is not None:
			name = os.path.join(self.get_path(), name)
			
		return name
		
	def set_server_addr(self, addr):
		self.cfg.set_str(ROOTKEY+'/wikserve', 'address', addr)
	
	def get_server_addr(self):
		return self.cfg.get_str(ROOTKEY+'/wikserve', 'address', '127.0.0.1')
	
	def set_server_port(self, port):
		self.cfg.set_int(ROOTKEY+'/wikserve', 'port', port)
	
	def get_server_port(self):
		return self.cfg.get_int(ROOTKEY+'/wikserve', 'port', 8080)
	
	def get_session_storage(self):
		return self.cfg.get_str(ROOTKEY+'/wikserve', 'session_storage', 'ram')		
	
	def set_session_storage(self, kind):
		"kind = 'ram' or 'file'"
		assert(kind in ('ram', 'file'))
		return self.cfg.set_str(ROOTKEY+'/wikserve', 'session_storage', kind)		
	
	def get_session_timeout(self):
		"Get session timeout, in minutes."
		return self.cfg.get_int(ROOTKEY+'/wikserve', 'session_timeout', 60)
	
	def set_session_timeout(self, timeout):
		"Set session timeout, in minutes."
		return self.cfg.set_int(ROOTKEY+'/wikserve', 'session_timeout', timeout)
	
	def get_link_unknown_camelwords(self):
		# XXX this is False by default since currently you have to turn the cache
		# off when enabling this, and also don't want to surprise existing users with
		# lots of autolinks suddenly appearing
		return self.cfg.get_bool(ROOTKEY+'/wikserve', 'link_unknown_camelwords', False)
	
	def set_link_unknown_camelwords(self, val):
		self.cfg.set_bool(ROOTKEY+'/wikserve', 'link_unknown_camelwords', val)
	
	def get_request_log_filters(self):
		"Get the user-defined list of LIKE clauses for filtering requests"
		return self.cfg.get_list(ROOTKEY+'/wikserve/logs', 'request_filters', [])
	
	def set_request_log_filters(self, filters):
		"Set the user-defined list of LIKE clauses for filtering requests"
		return self.cfg.set_list(ROOTKEY+'/wikserve/logs', 'request_filters', filters)
		
	def get_debug_flag(self):
		"Is the 'debug' flag set? (allowing access to debug commands)"
		return self.cfg.get_bool(ROOTKEY+'/wikserve', 'debug_flag', False)
		
	def set_debug_flag(self, value):
		self.cfg.set_bool(ROOTKEY+'/wikserve', 'debug_flag', value)
	
	def get_cache_flag(self):
		"Is the 'do_cache' flag set? (allowing caching of results)"
		return self.cfg.get_bool(ROOTKEY+'/wikserve', 'do_cache', True)
		
	def set_cache_flag(self, value):
		self.cfg.set_bool(ROOTKEY+'/wikserve', 'do_cache', value)
		self.update_rendercache()
	
	def get_cache_expire_time(self):
		# default is a week
		return self.cfg.get_int(ROOTKEY+'/wikserve', 'cache_expire_time', 60*60*24*7)
		
	def set_cache_expire_time(self, seconds):
		self.cfg.set_int(ROOTKEY+'/wikserve', 'cache_expire_time', seconds)
		self.update_rendercache()
	
	def get_cache_clean_interval(self):
		return self.cfg.get_int(ROOTKEY+'/wikserve', 'cache_clean_interval', 10000)
		
	def set_cache_clean_interval(self, count):
		self.cfg.set_int(ROOTKEY+'/wikserve', 'cache_clean_interval', count)
		self.update_rendercache()
		
	def get_metadb_flag(self):
		"Is the 'use_metadb' flag set?"
		return self.cfg.get_bool(ROOTKEY+'/wikserve', 'use_metadb', True)
		
	def set_metadb_flag(self, value):
		self.cfg.set_bool(ROOTKEY+'/wikserve', 'use_metadb', value)
	
	def set_safemode_timelimit(self, seconds):
		"Set max runtime for rendering content in safe mode."
		self.cfg.set_int(ROOTKEY+'/wikserve', 'safemode_timelimit', seconds)
	
	def get_safemode_timelimit(self):
		return self.cfg.get_int(ROOTKEY+'/wikserve', 'safemode_timelimit', 20)
		
	def get_skiplist(self):
		from wikklytext.wiki.render import get_item_skiplist
		return get_item_skiplist(self)

	def set_skiplist(self, namelist):
		from wikklytext.store import tags_join
		
		if 'DoNotRender' not in namelist:
			namelist.append('DoNotRender')
			
		item = WikklyItem('DoNotRender', tags_join(namelist), author='AutoContent')
		self.store().saveitem(item)

	# These next two provide a hook for the external caller to record updates
	# they have performed on the wiki. It is entirely up to the caller to define
	# what these updates mean. This is just for getting/recording them by name.
	def get_applied_updates(self):
		"""
		Get the set of updates that have been applied. 
		(The meaning of the updates is defined by the caller.)
		"""
		return set_(self.cfg.get_list(ROOTKEY, 'applied_updates', []))
		
	def add_applied_update(self, name):
		"""
		Add an update to the set of applied updates.
		(The meaning of the updates is defined by the caller.)
		"""
		s = self.get_applied_updates()
		s.add(name)
		self.cfg.set_list(ROOTKEY, 'applied_updates', list(s))
		
	def set_user_plugin_dirs(self, dirs):
		self.cfg.set_list(ROOTKEY+'/core', 'user_plugin_dirs', dirs)
		
	def get_user_plugin_dirs(self):
		return self.cfg.get_list(ROOTKEY+'/core', 'user_plugin_dirs', [])
		
	#----------------------------------------------------------------
	# Wiki users (stored in USERDB)
	#
	# Users are identified by one of the following strings (in
	# WikklyItem.author):
	#    "0"            - UID for wiki admin/superuser. Look up name,
	#                     password, privs, etc. in USERDB.
	#    Other string   - Look up in USERDB. If exists, use name, password,
	#                     privs, etc. for user. If not found, assume 
	#                     non-priviledged user and show name as-is in rendered content.
	#
	# Most user_* routines take a UID to provide unambiguous lookup
	# in case of duplicate usernames.
	#----------------------------------------------------------------
	def user_create(self, UID, username, email, can_login, password, safe_mode):
		"""
		Create a new user:
			UID: UID for user:
			       Pass "0" for superuser.
				   For normal users, this can be any other string.
				   In a multiuser/multithreaded setting, it is strongly recommended that
				   you generate UIDs with boodebr.util.guid.makeGUID().
				   In a single-threaded setting, you can pass anything for UID,
				   just make sure it is not already used (with user_valid_UID()).
			username: User name
			email: Email address
			can_login: True/False - is this user allowed to login?
			password: Plaintext password (only used if can_login is True)
			safe_mode: True/False if this user's content should be
			           rendered in safe mode.
					   
		Returns True if created OK.
		Returns False if not (username already exists).
		"""
		# The code below tries to not create a duplicate username, but
		# it could still be possible in a race condition. However, the two users 
		# will still have separate UIDs, so its just an issue on how they log in.
		
		# check before creating
		if self.user_exists(username):
			return False
		
		self.userdb.set_str(USERDBKEY+'/'+UID, 'username', username)
		self.userdb.set_str(USERDBKEY+'/'+UID, 'email', email)
		
		if can_login:
			self.userdb.set_str(USERDBKEY+'/'+UID, 'pwdhash', makeSHA(password).hexdigest())
		else: # set to impossible hash value to prevent user from logging in
			self.userdb.set_str(USERDBKEY+'/'+UID, 'pwdhash', '')
			
		self.userdb.set_bool(USERDBKEY+'/'+UID, 'safe_mode', safe_mode)

		# check again after creating
		if len(self.user_getUIDs(username)) > 1:
			# >1 UID with my username; delete self and try again
			self.userdb.delete_path(USERDBKEY, UID)
			return False
			
		# created OK
		return True

	def user_all_UIDs(self):
		"""
		Return a list of all UIDs in userdb.
		"""
		return self.userdb.list_paths(USERDBKEY)
		
	def user_valid_UID(self, UID):
		"Does the given UID exist?"
		return UID in self.user_all_UIDs()
		
	def user_getUIDs(self, username):
		"""
		Return all UIDs associated with username (normally only zero or one, 
		but caller should assume that more than one is possible).
		"""
		uids = []
		for uid in self.user_all_UIDs():
			if self.userdb.get_str(USERDBKEY+'/'+uid, 'username', None) == username:
				uids.append(uid)
				
		return uids
		
	def user_exists(self, username):
		"Convenience: Does the given username exist?"
		return len(self.user_getUIDs(username)) > 0
	
	def user_set_username(self, UID, username):
		"Set user's username."		
		self.userdb.set_str(USERDBKEY+'/'+UID, 'username', username)
	
	def user_get_username(self, UID):
		"""
		Try to lookup username given a UID.
		
		If invalid UID given, returns UID as-is.
		"""
		# do NOT do lookup without verifying it is a valid UID.
		# this prevents creating empty users when looking up
		# non-UIDs.
		if not self.user_valid_UID(UID):
			return UID
			
		return self.userdb.get_str(USERDBKEY+'/'+UID, 'username', None)
	
	def user_set_password(self, UID, password):
		"Set user's password to given (cleartext) password."		
		self.userdb.set_str(USERDBKEY+'/'+UID, 'pwdhash', makeSHA(password).hexdigest())
	
	def user_set_email(self, UID, email):
		"Set user's email address."		
		self.userdb.set_str(USERDBKEY+'/'+UID, 'email', email)
	
	def user_get_email(self, UID):
		uids = self.user_all_UIDs()
		if UID not in uids:
			return None
			
		return self.userdb.get_str(USERDBKEY+'/'+UID, 'email', None)
			
	def user_set_safemode(self, UID, safe_mode):
		"Set True/False if user's content should render in safe mode."		
		self.userdb.set_bool(USERDBKEY+'/'+UID, 'safe_mode', safe_mode)
	
	def user_get_safemode(self, UID):
		"Return True/False if users content should be rendered in 'safe' mode."
		uids = self.user_all_UIDs()
		if UID not in uids:
			return True # use safe mode for any unknown users
		
		return self.userdb.get_bool(USERDBKEY+'/'+UID, 'safe_mode', True)
	
	def user_can_login(self, UID):
		"Is the given user allowed to login (assuming they know the username/password)?"
		return len(self.userdb.get_str(USERDBKEY+'/'+UID, 'pwdhash', None)) > 0
		
	def user_check_password(self, UID, password):
		"""
		Check a users password (given plaintext password).
		
		Returns True if matches, False if not.
		"""		
		s = self.userdb.get_str(USERDBKEY+'/'+UID, 'pwdhash', None)
		if s is None:
			return False # no such user
			
		return makeSHA(password).hexdigest() == s
			
	# Convenience - bring these up from the wikStore
	def names(self):
		"""
		Return names of all content items in store as a list of strings.
		"""
		return self.store().names()
		
	def getitem(self, name):
		"""
		Load a single content item from the store.
		
		Returns WikklyItem, or None if item not found.
		
		NOTE: If you are looping over all items, you should
		use getall() instead of getitem() since it is a lot
		faster for some store types.
		"""
		return self.store().getitem(name)
		
	def getall(self):
		"""
		Load all content from store.
		
		Returns list of WikklyItems.
		"""
		return self.store().getall()
		
	def saveitem(self, item, oldname=None):
		"""
		Save a WikklyItem to the store.
		
		If oldname != None, passed item replaces the item of the given name.
		Notes:
			* Passing oldname=None is the way to store a new item, or
			  overwrite an existing item.
			* Passing oldname=item.name is the same as passing oldname=None
		"""
		self.store().saveitem(item, oldname)
		
	def search(self, query):
		"Return a list of items matching query."
		return self.store().search(query)
		
	# cache
	def cacheable(self, item=None):
		"Is the given item cacheable? If item is None, returns global caching flag."
		if self.get_cache_flag() and (item is None or not item.has_tag('-cache')):
			return True
		else:
			return False
		
	def rendercache(self):
		"Return my rendering cache object."
		if self._rendercache is None:
			self.update_rendercache()
			
		return self._rendercache
		
	def macro_handler(self, name, context, *elements):
		"""
		Custom macro handler.
		
		Returns (handled, result)
		"""
		from wsgifront import normheaders
		from wikklytext.base import StringIO
		
		env = self.getRT_wsgienv()
		
		# env is already a normalized copy, so just add my headers
		env['wsgifront.x-wikklytext-wiki'] = self
		env['wsgifront.x-wikklytext-UID'] = self.getRT_curUID()
		
		plugins = self.load_plugins()
		
		if name in plugins.wsgi_macros:
			func = plugins.wsgi_macros[name]
			result = func(env, *elements)
			# handled
			return True, result
		else:
			# not handled
			return False,None
		
	def reserved_names(self):
		"""
		Names reserved by renderer and cannot be used as
		item names by user.
		"""
		return set_(['DoNotRender','index','index-Names','index-Tags',
					'index-Timeline'])
					
	def renderable_items(self, logfunc=nopfunc):
		"""
		Return a list of all renderable items in the store.
		
		Returns list of:
			(item, html_name)
		"""
		items = []
		skipset = set_(self.get_skiplist())
		regen_all = False
		
		# much faster to use getall() for some store types
		for item in self.store().getall():
			if item.name in skipset:
				# ignore item
				continue
			
			if item.name in self.reserved_names():
				print "*** WARNING - Name '%s' is reserved by WikklyText. Will not render." % item.name
				continue
				
			# make HTML filename
			if item.name == 'DefaultTiddlers':
				fsname = self.fpath('index.html')
			else:
				fsname = self.fpath(makeFSname(item.name) + '.html')
			
			items.append((item, fsname))
		
		# if DefaultTiddlers does not exist, make empty one
		allnames = [i[0].name for i in items]
		if 'DefaultTiddlers' not in allnames:
			d = WikklyItem('DefaultTiddlers')
			items.append((d, self.fpath('index.html')))
		
		return items
		
	def render(self, namelist=None, uid=None, logfunc=nopfunc, oneitem=None):
		"""
		namelist or oneitem can be used to only render certain items:
			* If namelist is not None, only those names will be rendered.
			   namelist can include special names like 'index', 'index-Timeline', etc.,
			   to render the indexes.
			* If oneitem is not None, it must be a WikklyItem to be rendered.
			* Only (at most) one of namelist and oneitem can be given.
			
		uid, if given, is the logged-in UID (for customizing display)
		None means no logged-in user.
			
		All items are rendered to memory and returned as a map of:
			map[item_name] = (fsname, rendered_html)
			
		Where 'fsname' is the full path name (if the caller wants to save
		the rendered file). 'rendered_html' is the HTML, ready to be served.
		"""
		from wikklytext.wiki.layout import layoutPage, layoutTimelinePage, \
				layoutNameIndexPage, layoutTagIndexPage  
		from time import time
		
		# API check
		assert(namelist is None or oneitem is None) # cannot BOTH be given
		
		rendered = {}
		
		# turn 'index' into 'DefaultTiddlers'
		if namelist is not None:
			try:
				i = namelist.index('index')
				namelist[i] = 'DefaultTiddlers'
				replaced_index = True
			except ValueError:
				replaced_index = False
		else:
			replaced_index = False
			
		# make list of (item,fsname) to render
		if oneitem is None:
			# if caller provided a namelist, only render those names
			allitems = [(item,fsname) for item,fsname in self.renderable_items(logfunc) if \
							namelist is None or item.name in namelist]
		else:
			# only render 'oneitem'
			allitems = [(oneitem, self.fpath(makeFSname(item.name) + '.html'))]
				
		logfunc("Info: ")
		logfunc(self.store().info())
		logfunc("Rendering ...")
		for item,fsname in allitems:
			t0 = time()		
			logfunc("   Rendering %s ..." % os.path.basename(fsname))
			html = layoutPage(self, item, uid)
			t1 = time()
			
			#sys.stdout.write("\b\b\b %.1f secs\n" % (t1-t0))
			#t0 = time()
			# turn 'DefaultTiddlers' into 'index' as needed
			if item.name == 'DefaultTiddlers' and replaced_index:
				rendered['index'] = (fsname, html) # caller asked for 'index' not 'DefaultTiddlers'
			else:
				rendered[item.name] = (fsname, html)
				
			#t1 = time()
			#print "\b\b\b %.1f secs  " % (t1-t0)
		
		# NOTE: Don't change the names of the index-* files without
		# changing the URLResolver in wiki/render.py also.
		
		# write timeline index
		if namelist is None or 'index-Timeline' in namelist:
			logfunc("   Writing timeline index")
			html = layoutTimelinePage(self, uid)
			rendered['index-Timeline'] = (self.fpath('index-Timeline.html'), html)
			
		# write name index
		if namelist is None or 'index-Names' in namelist:
			logfunc("   Writing name index")
			html = layoutNameIndexPage(self, uid)
			rendered['index-Names'] = (self.fpath('index-Names.html'), html)
			
		# write tag index
		if namelist is None or 'index-Tags' in namelist:		
			logfunc("   Writing tag index")
			html = layoutTagIndexPage(self, uid)
			rendered['index-Tags'] = (self.fpath('index-Tags.html'), html)
		
		return rendered
		
	def store(self, logfunc=nopfunc):
		"Open and return my wikStore."
		if hasattr(self, '_my_store'):
			return self._my_store
			
		from wikklytext.store.wikStore_Q import wikStore_Q
		
		# note: do NOT cache results - this causes errors in wikStore_sqlite when
		# multiple threads try and access the same connection
		#from wikklytext.store import wikStore_files, wikStore_sqlite, wikStore_tw
	
		if not self.initted():
			raise Exception("** No wiki here - run 'wik init' first.")
			
		kind = self.get_kind()
		if kind == 'text':
			logfunc("OPENING STORE (%s,%s)" % (kind, self.get_path()))
			store = wikStore_Q('text', self.get_path())
		elif kind == 'tiddlywiki':
			logfunc("OPENING STORE (%s,%s)" % (kind, self.get_filename()))
			store = wikStore_Q('tiddlywiki', self.get_filename())
		elif kind == 'sqlite':
			logfunc("OPENING STORE (%s,%s)" % (kind, self.get_filename()))
			store = wikStore_Q('sqlite', self.get_filename())
		else:
			raise Exception("Bad kind")

		self._my_store = store
		return store
	
	def itemname_from_fsname(self, fsname):
		"""
		Given a fsname (from makeFSname, i.e. no extension), return the 
		corresponding item name, or None if not found.
		"""
		# check special names
		if fsname in ['index','index-Names','index-Tags','index-Timeline']:
			return fsname
			
		for item in self.store().getall():
			if makeFSname(item.name) == fsname:
				return item.name
				
		return None
	
