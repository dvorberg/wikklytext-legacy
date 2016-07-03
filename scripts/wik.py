"""
wik.py: Meta-tool for managing WikklyText-based wikis.

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

DO_PROFILING = 0

from optparse import OptionParser, IndentedHelpFormatter
import os, sys, re
from boodebr.config import *
from wikklytext.store import WikklyItem, makeFSname
from wikklytext.wiki import WikklyWiki
from wikklytext.port import *
from boodebr.util import makeGUID
import shutil

def echo(s):
	print s
	
class Formatter(IndentedHelpFormatter):
	def __init__(self):
		IndentedHelpFormatter.__init__(self)
		
	def format_description(self, desc):
		return desc or ""
				
def wik_open(path):
	from wsgifront import normheaders
	from StringIO import StringIO
	w = WikklyWiki(path)
	
	# wiki assumes it is talking to a WSGI environment so have to make a fake one --
	# the server info is never used so is doesn't matter what values are chosen
	fake_env = {'REQUEST_METHOD':'GET', 'SERVER_NAME':'localhost', 'SERVER_PORT':80,
				'SERVER_PROTOCOL': 'HTTP/1.0', 'SCRIPT_NAME':'', 'PATH_INFO':''}
	w.setRT_wsgienv(normheaders(fake_env, 'will be removed', StringIO(''),
			StringIO(), False,False,True))
	return w
	
def wik_ls(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
		
	store = wiki.store()
	
	print "Info: "
	print "   ",store.info()
	names = store.names()
	names.sort(lambda a,b: cmp(a.lower(),b.lower()))
	print "Wiki contains %d entries:" % len(names)
	for name in names:
		print "   ",name

def wik_clean(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
		
	for item in wiki.store().getall():
		fname = os.path.join(wiki.get_path(), makeFSname(item.name) + '.html')
		if os.path.isfile(fname):
			print "Remove %s" % fname
			os.unlink(fname)
			
	for name in ['index.html', 'index-Timeline.html', 'index-Names.html',
					'index-Tags.html']:
		if os.path.isfile(name):
			print "Remove %s" % name
			os.unlink(name)
		
	# clear cache as well
	print "Clearing cache ..."
	wiki.rendercache().clear_all()

def wik_cache(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return

	while 1:
		no_show = ['SiteTitle', 'SiteSubtitle', 'DefaultTiddlers', 'DoNotRender']

		print "\nAll wiki items:"
		print "---------------"
		
		items = [item for item in wiki.getall() if item.name not in no_show]
		for i,item in enumerate(items):
			if item.has_tag('-cache'):
				print "%3d: %s (-NOCACHE-)" % (i,item.name)
			else:
				print "%3d: %s" % (i,item.name)
		
		sys.stdout.write("\nToggle '-cache' flag for item (or ENTER to exit): ")
		ans = sys.stdin.readline()
		try:
			i = int(ans)
		except:
			return
		
		items[i].tag_toggle('-cache') 
		wiki.saveitem(items[i])	
		
def wik_skip(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
	
	while 1:
		skipped = set_(wiki.get_skiplist())
		
		no_show = ['SiteTitle', 'SiteSubtitle', 'DefaultTiddlers', 'DoNotRender']
		names = wiki.store().names()
		names = [name for name in names if name not in no_show]
		
		print "\nAll wiki items:"
		print "---------------"
		
		for i,name in enumerate(names):
			if name in skipped:
				print "%3d: %s (-SKIPPED-)" % (i,name)
			else:
				print "%3d: %s" % (i,name)
			
		sys.stdout.write("\nToggle 'skip' flag for item (or ENTER to exit): ")
		ans = sys.stdin.readline()
		try:
			i = int(ans)
		except:
			return
		
		if names[i] in skipped:
			skipped.remove(names[i])
		else:
			skipped.add(names[i])
			
		wiki.set_skiplist(list(skipped))
		# adding a previously rendered item to the skiplist messes
		# up the cache (causes index files to always be rebuilt) so
		# just clear cache when changing the skiplist
		wiki.rendercache().clear_all()
		
def wik_render(wikipath, namelist = None):
	from wikklytext import copy_CSS_elements
	from wikklytext.wiki.rss import create_rss_xml
	
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return

	# render items (to memory)
	rendered = wiki.render(namelist, uid=None, logfunc=echo) # render generic pages, no user logged-in

	# write files
	print "Writing files ..."
	for name, (fsname, html) in rendered.items():
		open(fsname, 'wb').write(html)
		
	if not os.path.isdir(wiki.get_css_path()):
		os.makedirs(wiki.get_css_path())
	
	# render rss.xml
	print "Creating rss.xml ..."
	xml = create_rss_xml(wiki, '')
	open('rss.xml', 'wb').write(xml)
	
	copy_CSS_elements(wiki.get_css_path())
	
	st = wiki.rendercache().stats()
	#print "rendered: %d, tried_cache: %d, cache_hits: %d" % \
	#		(st.nr_renders, st.nr_tried_cache, st.nr_cache_hits)
	#print "cached:   %8d bytes in, %8d bytes out, %f secs" % \
	#		(st.bytes_cached_in, st.bytes_cached_out, st.secs_cached)
	#print "uncached: %8d bytes in, %8d bytes out, %f secs" % \
	#		(st.bytes_uncached_in, st.bytes_uncached_out, st.secs_uncached)
	#print "total:    %8d bytes in, %8d bytes out, %f secs" % \
	#		(st.bytes_cached_in+st.bytes_uncached_in,
	#			st.bytes_cached_out+st.bytes_uncached_out, 
	#			st.secs_cached+st.secs_uncached)

	print "cache-stats:"
	print "   type:    %s" % st['type']
	print "   puts:    %d" % st['puts']
	print "   gets:    %d" % st['gets']
	print "   hits:    %d" % st['hits']
	print "   %%hits:   %.1f" % (st['hits']*100.0/st['gets'])
	print "   objects: %d" % st['objects']
	print "   bytes:   %d" % st['bytes']
	print '   expiration_time %d' % st['expiration_time']
	print '   clean_interval %d' % st['clean_interval']
	
def item_post_conv(wiki, item, backups):
	from wikklytext.store import makeFSname
	
	if wiki.get_kind() == 'text':
		# move original .txt file to backups
		txt = os.path.join(wiki.get_path(), makeFSname(item.name) + '.txt')
		shutil.copy(txt, backups)
		os.unlink(txt)
	elif wiki.get_kind() in ['tiddlywiki', 'sqlite']:
		# nothing to cleanup for items
		pass
	else:
		raise Exception("Don't know what to do with %s" % wiki.get_kind())
		
def conv_check_ok(wiki, newkind, newpath):
	from wikklytext.store import makeFSname

	if newkind in ['tiddlywiki', 'sqlite']:
		if os.path.exists(newpath):
			print "'%s' exists - not overwriting" % newpath
			return False
			
	elif newkind == 'text':
		for item in wiki.getall():
			txt = os.path.join(wiki.get_path(), makeFSname(item.name) + '.txt')
			if os.path.exists(txt):
				print "'%s' would be overwritten by conversion -- exiting now." % txt
				return False
				
	else:
		raise Exception("Unknown conversion")
		
	return True
	
def wiki_post_conv(wiki, newkind, newpath, backups):
	import wikklytext.store.wikStore_Q as wikStore_Q
	import boodebr.sql.sqliteQ as sqliteQ
	
	oldname = wiki.get_filename()
	oldkind = wiki.get_kind()
	
	# change to new store
	wiki.set_kind(newkind)
	wiki.set_filename(newpath)

	# release any open files before trying to move old wiki
	del wiki
	wikStore_Q.shutdown()
	sqliteQ.shutdown()
	
	if oldkind == 'text':
		# content already moved
		pass
	elif oldkind in ('tiddlywiki','sqlite'):
		shutil.copy(oldname, backups)
		os.unlink(oldname)
	else:
		raise Exception("Bad kind")
		
def wik_do_conv(wiki):
	print "\nCurrent format is '%s'" % wiki.get_kind()
	print "\nSelect new format:"
	print "   1) Text files"
	print "   2) TiddlyWiki file"
	print "   3) SQLite database"
	sys.stdout.write('\nSelection: ')
	ans = sys.stdin.readline()
	try:
		i = int(ans)
	except:
		return
		
	if i == 1:
		newkind = 'text'
		newpath = '.'
	elif i == 2:
		newkind = 'tiddlywiki'
		sys.stdout.write('Enter new TiddlyWiki filename [wiki.html]: ')
		newpath = sys.stdin.readline().lstrip().rstrip()
	elif i == 3:
		newkind = 'sqlite'
		sys.stdout.write('Enter new database filename [wiki.db]: ')
		newpath = sys.stdin.readline().lstrip().rstrip()
	else:
		raise Exception("Bad kind")
		
	if not len(newpath):
		if i == 3: 
			newpath = 'wiki.db'
		elif i == 2:
			newpath = 'wiki.html'
		else:
			raise Exception("Internal error")

	if not conv_check_ok(wiki, newkind, newpath):
		return
		
	if not os.path.exists('BACKUPS'):
		defbackups = 'BACKUPS'
	else:
		j = 1
		while os.path.exists('BACKUPS-%d' % j):
			j += 1
			
		defbackups = 'BACKUPS-%d' % j
		
	sys.stdout.write("Backup current content to [%s]: " % defbackups)
	backups = sys.stdin.readline().lstrip().rstrip()
	if not len(backups):
		backups = defbackups
		
	if not os.path.isabs(backups):
		backups = os.path.join(wiki.get_path(), backups)
		
	if not os.path.isdir(backups):
		os.makedirs(backups)
		
	if i == 1:
		from wikklytext.store import wikStore_files
		new_class = wikStore_files
		new_kind = 'text'
	elif i == 2:
		from wikklytext.store import wikStore_tw
		new_class = wikStore_tw
		new_kind = 'tiddlywiki'
	elif i == 3:
		from wikklytext.store import wikStore_sqlite
		new_class = wikStore_sqlite
		new_kind = 'sqlite'
		
	out = new_class(newpath)
	for name in wiki.names():
		print "Converting %s" % name
		item = wiki.getitem(name)
		out.saveitem(item)
		# perform post-conversion step
		item_post_conv(wiki, item, backups)
		
	wiki_post_conv(wiki, newkind, newpath, backups)
			
	print "Conversion complete. Original files moved to '%s'" % backups
	
def wik_conv(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
	
	wik_do_conv(wiki)
	
def wik_trustall(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return

	print "\n***** PLEASE READ **********************************************"
	print "**"
	print "** This will create accounts for ALL content authors (who do not"
	print "** already have accounts on your wiki) and mark them 'trusted'."
	print "**"
	print "** You should NOT do this if you are concerned there might be"
	print "** users on your wiki that have created malicious content."
	print "**"
	print "****************************************************************"
	
	sys.stdout.write("\nContinue (y/n)?: ")
	ans = sys.stdin.readline()
	if len(ans) == 0 or ans[0] != 'y':
		print "** Cancelling action **"
		return
		
	store = wiki.store()
	
	#print "ALL UIDS",wiki.user_all_UIDs()
	
	for item in store.getall():
		# if author already set to a UID, leave it as-is
		if item.author == '0' or wiki.user_valid_UID(item.author):
			#print "%s: Not changing" % repr(item.name)
			continue
			
		# if "item.author" can be used as a UID, use it. this keeps
		# me from having to rewrite the TW (making the author links
		# look bad when viewing as a TW; when viewing in wikserve
		# they look correct either way).
		if not wiki.user_exists(item.author):
			if not wiki.user_valid_UID(item.author):
				# since I'm running single threaded, I can do this
				# instead of using makeGUID() and know the UID will not exist.
				uid = item.author
			else:
				uid = makeGUID(item.author)
			
			print "ADD AUTHOR",item.author,uid
			
			# add as an unrestricted user who cannot login
			wiki.user_create(uid, item.author, '', False, '', False)
		else:
			uids = wiki.user_getUIDs(item.author)
			if len(uids) != 1:
				raise Exception("Need exactly one UID here!")
				
			uid = uids[0]
			
		# set author to uid
		print "%s: Set author" % item.name
		item.author = uid
		store.saveitem(item)
		
def echo_cb(cbdata, msg, pctdone):
	#print msg
	print "%d%% %s" % (pctdone,msg)
	
def make_default_content(wiki, callback=echo_cb, cbdata=None):
	"Create some default content (careful not to overwrite existing items)."
	import wikklytext.wiki.defcontent as defcontent
	# make a user to generate content under
	uid = makeGUID('AutoContent')
	# give full privs, but don't allow login
	wiki.user_create(uid, 'AutoContent', '', can_login=False, password='', safe_mode=False)
	
	store = wiki.store()
	names = store.names()
	
	if 'HelloWorld' not in names:
		callback(cbdata, 'Adding HelloWorld', 10)
		item = WikklyItem('HelloWorld', defcontent.HelloWorld,
				author=uid)
		store.saveitem(item)				
	
	if 'DefaultTiddlers' not in names:
		callback(cbdata, 'Adding DefaultTiddlers', 14)
		item = WikklyItem('DefaultTiddlers', defcontent.DefaultTiddlers, author=uid)
		store.saveitem(item)
		
	if 'SiteTitle' not in names:
		callback(cbdata, 'Adding SiteTitle', 18)
		item = WikklyItem('SiteTitle', defcontent.SiteTitle, author=uid)
		store.saveitem(item)
	
	if 'SiteSubtitle' not in names:
		callback(cbdata, 'Adding SiteSubtitle', 22)
		item = WikklyItem('SiteSubtitle', defcontent.SiteSubtitle, author=uid)
		store.saveitem(item)
	
	if 'DoServerCmd' not in names:
		callback(cbdata, 'Adding DoServerCmd', 26)
		item = WikklyItem('DoServerCmd', defcontent.DoServerCmd, author=uid)
		store.saveitem(item)
	
	if 'MarkupReference' not in names:
		callback(cbdata, 'Adding MarkupReference', 30)
		item = WikklyItem('MarkupReference', defcontent.MarkupReference, author=uid)
		store.saveitem(item)
	
	if 'MultiLingual' not in names:
		callback(cbdata, 'Adding MultiLingual', 34)
		item = WikklyItem('MultiLingual', "<<include doc/MultiLingual.txt>>", author=uid)
		store.saveitem(item)
	
	# add an AutoContent item (saved under UID!)
	if uid not in names:
		callback(cbdata, 'Adding AutoContent', 38)
		item = WikklyItem(uid, "AutoContent is the author name used for automatically generated content.", 
							author=uid, tags=['auto-content'])
		store.saveitem(item)
	
	if 'StyleSheet' not in names:
		callback(cbdata, 'Adding StyleSheet', 42)
		item = WikklyItem('StyleSheet', defcontent.StyleSheet,			
							author=uid)
		store.saveitem(item)

	if 'MainMenu' not in names:
		callback(cbdata, 'Adding MainMenu', 46)
		item = WikklyItem('MainMenu', defcontent.MainMenu, author=uid)
		store.saveitem(item)
	
	if 'MarkupPreHead' not in names:
		callback(cbdata, 'Adding MarkupPreHead', 50)
		item = WikklyItem('MarkupPreHead', defcontent.MarkupPreHead, author=uid)
		store.saveitem(item)

	if 'MarkupPostHead' not in names:
		callback(cbdata, 'Adding MarkupPostHead', 54)
		item = WikklyItem('MarkupPostHead', defcontent.MarkupPostHead, author=uid)
		store.saveitem(item)

	if 'MarkupPreBody' not in names:
		callback(cbdata, 'Adding MarkupPreBody', 58)
		item = WikklyItem('MarkupPreBody', defcontent.MarkupPreBody, author=uid)
		store.saveitem(item)

	if 'MarkupPostBody' not in names:
		callback(cbdata, 'Adding MarkupPostBody', 60)
		item = WikklyItem('MarkupPostBody', defcontent.MarkupPostBody, author=uid)
		store.saveitem(item)

def do_create_wiki(path, kind, filename, server_addr, server_port, callback=echo_cb, cbdata=None,
					noupdate=False):
	"""
	Create and initialize a wiki. Will NOT overwrite an existing wiki.
	
		path: Root folder for wiki
		kind: 'text', 'tiddlywiki', 'sqlite'
		filename: for tiddlywiki|sqlite, the filename for the store
		server_addr: server address (string)
		server_port: server port (int)
		callback: Progress callback, see echo_cb() for args.
		cbdata: Arg passed to callback.
		noupdate: Do not update wiki after creating (for debugging purposes only)
	"""
	if not os.path.isdir(path):
		os.makedirs(path)
		
	callback(cbdata, 'Initializing wiki in "%s" ...' % path, 0)
	
	wiki = wik_open(path)
	if wiki.initted():
		raise Exception("** wiki already exists here - not overwriting")
		
	wiki.do_init()
	wiki.set_kind(kind)
	if kind in ['tiddlywiki', 'sqlite']:
		if filename is None:
			raise Exception("Filename required")
			
		wiki.set_filename(filename)
		
	wiki.set_server_addr(server_addr)
	wiki.set_server_port(server_port)
	
	# make autolinks to unknown camelwords by default
	wiki.set_link_unknown_camelwords(True)
	
	callback(cbdata, "Generating default content ...", 5)
	
	make_default_content(wiki, callback, cbdata)
		
	callback(cbdata, "Updating metadata ...", 60)
	
	# initialize wiki metadata
	# ** Must do this AFTER 'make_default_content' so that the
	# ** update process can apply any updates needed on the wiki itself.
	if not noupdate:
		wik_updatemeta(wiki.get_path())
	
def wik_init(wikipath, oldfmt=False):
	wiki = wik_open(wikipath)
	if wiki.initted():
		print "** wiki already exists here - not overwriting"
		return
		
	del wiki
	
	print "\nSelect storage format:"
	print "  1. Text (.txt) files"
	print "  2. TiddlyWiki (.html) file"
	print "  3. SQLite database"
	sys.stdout.write("\nChoice: ")
	ans = sys.stdin.readline().rstrip()
	ans = int(ans)
	
	if ans == 1:
		kind = 'text'
		filename = None
		
	elif ans == 2:
		print "\n**** PLEASE READ *****************************************************"
		print "**"
		print "** Before using an existing TiddlyWiki file, I STRONGLY recommend"
		print "** recommend that you follow these steps:"
		print "**   1. Exit this program (Ctrl-C, etc.)"
		print "**   2. Create an empty folder."
		print "**   3. Copy your wiki to the empty folder."
		print "**   4. Run 'wik init' in the new folder."
		print "**"
		print "** This will prevent you from accidentally damaging your wiki,"
		print "** or other files that are in the same folder, until you"
		print "** become familiar with how 'wik' works."
		print "**"
		print "************************************************************************"
		print ""
		
		kind = 'tiddlywiki'
		sys.stdout.write("Enter filename (will create if does not exist) [wiki.html]: ")
		filename = sys.stdin.readline().rstrip()
		if not len(filename):
			filename = 'wiki.html'
			
	elif ans == 3:
		kind = 'sqlite'
		sys.stdout.write("Enter filename (will create if does not exist) [wiki.db]: ")
		filename = sys.stdin.readline().rstrip()
		if not len(filename):
			filename = 'wiki.db'
		
	print "\n * The following options only affect 'wikserve'. If you do not care about"
	print " * using 'wikserve' then just accept the defaults.\n"
	
	sys.stdout.write("Enter address for local server [127.0.0.1]: ")
	addr = sys.stdin.readline().rstrip()
	if not len(addr):
		addr = '127.0.0.1'
	
	if not re.match('127\.', addr):
		print ""
		print "****************************************************************************"
		print "**"
		print "** Fair Warning **"
		print "**"
		print "** 'wik serve' has not been heavily tested on a publically-accessible"
		print "** site or audited by third parties for security issues."
		print "**"
		print "** Use caution when deciding to serve a public site with 'wik serve'"
		print "**"
		print "****************************************************************************"
		print ""
		
	sys.stdout.write("Enter port for local server [8000]: ")
	port = sys.stdin.readline().rstrip()
	if not len(port):
		port = '8000'
	
	port = int(port)
	
	# create wiki
	do_create_wiki(wikipath, kind, filename, addr, port, noupdate=oldfmt)
	
	print "\nYou can now run 'wik render' or 'wik serve' to render/serve your wiki content.\n"
		
def do_updatemeta(wiki, callback=None, cbdata=None):
	"""
	Don't call directly - should only be called from metadata.MetaUpdater.
	"""
	from boodebr.sql import load_pysqlite
	from boodebr.sql.sqliteQ import sqliteQ
	import wikklytext.wiki.metadata as metadata
	import datetime as DT
	
	callback = callback or echo_cb
	
	# run any wiki updates
	if metadata.wiki_needs_update(wiki):
		metadata.wiki_apply_updates(wiki, callback, cbdata)
		
	# run any metadata updates
	if load_pysqlite() is None:
		return
		
	n = DT.datetime.now()
	stamp = '%d-%02d-%02d-%02d%02d%02d%d' % \
			(n.year, n.month, n.day, n.hour, n.minute, n.second, n.microsecond)
			
	name = wiki.metadata_dbname()
	if not os.path.isfile(name):
		print "Creating %s" % name
		sql = sqliteQ(name)
		metadata.createdb(sql)
	else:
		# create backup before upgrading
		Bname = name + '-BACKUP-' + stamp
		print "Backing up %s -> %s" % (name, Bname)
		shutil.copy(name, Bname)
		sql = sqliteQ(name)
	
	# run any updates
	metadata.updatedb(sql, callback, cbdata)
	
def wik_updatemeta(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
	
	from wikklytext.wiki.metadata import MetaUpdater
	updater = MetaUpdater(wiki)
	updater.do_updates(echo_cb)
	
def wik_makeboot(wikipath):
	wiki = wik_open(wikipath)
	if not wiki.initted():
		print "** Error - no wiki found here."
		return
	
	from pkg_resources import resource_string
	# load file as resource
	buf = resource_string('wikklytext.scripts','wikboot.py')
	open(os.path.join(wiki.get_path(), 'wikboot.py'), 'wb').write(buf)
	
	print ""
	print "** Bootfile setup"
	print "** Edit 'wikboot.py' for tips on setting up Apache."
	print "** MAKE SURE to set WEBPATH!"
	print ""
	
def main():
	import wikklytext.version as version
	kws = {
		'usage': 'wik [options] command',
		'description': """A WikklyText meta-wiki tool.

Primary commands:
   clean     Removed all generated files.
   init      Initialize a wiki in the current directory.
   ls        List wiki content.
   render    Render wiki to HTML
   serve     Serve wiki through standalone HTTP server
   
Advanced:
   cache       Edit the list of items that should not be cached.
   conv        Convert wiki to another format (text, SQLite, TiddlyWiki)
   makeboot    Add bootstrap module to wiki, for use with mod_python.
   skip        Edit the list of items to exclude from rendering.
   trustall    Mark all existing authors as trusted (so their content
               will render in Full mode).
   updatemeta  Update wiki meta-database. May be needed after upgrading
               to a newer version of WikklyText. Safe to run multiple times.
""",
		'formatter': Formatter(),
		}
	parser = OptionParser(**kws)
	parser.add_option("-d", "--directory", dest='wikipath',	
				help='Specify wiki directory', default=os.getcwd())
	parser.add_option("", "--no-respawn", dest='norespawn',
				action='store_true', default=False,
				help='Do not auto-restart wiki server on exit')
	parser.add_option("", "--cfgpath", dest="configpath",
				help="Configuration path for 'wik gui'", default=None)
	parser.add_option('', '--oldfmt', dest='oldformat',
				action='store_true', default=False,
				help='(*Debugging*) Do not update metadata when creating a new wiki')
	parser.add_option('-v', '--version', dest='show_version',
				action='store_true', default=False,
				help='Show version number and exit')
	
	opts,args = parser.parse_args()
	if len(args) > 1:
		print "wik version %s, Copyright (C) 2007,2008 Frank McIngvale\n" % version.VSTR
		parser.print_help()
		return

	if opts.show_version:
		print 'WikklyText version %s' % version.VSTR
		return
		
	import wikklytext.store.wikStore_Q as wikStore_Q
	import boodebr.sql.sqliteQ as sqliteQ
	
	if len(args) == 0:
		cmd = 'gui' # default command if none given
	else:
		cmd = args[0]
	
	if cmd not in ['serve']:
		wikStore_Q.start() # wikserve does this itself
		sqliteQ.start()
		
	try:	
		wikipath = os.path.abspath(opts.wikipath)
		
		if cmd == 'init':
			wik_init(wikipath, opts.oldformat)
		elif cmd == 'ls':
			wik_ls(wikipath)
		elif cmd == 'render':
			if DO_PROFILING:
				import cProfile, profile, pstats
				cProfile.runctx('wik_render(wikipath)', 
						{'wik_render': wik_render,
						 'wikipath': wikipath},{},'stats.ooo')
				st = pstats.Stats('stats.ooo')
				st.sort_stats('time')
				st.print_stats(.05)
			else:
				wik_render(wikipath)
			
		elif cmd == 'skip':
			wik_skip(wikipath)
		elif cmd == 'clean':
			wik_clean(wikipath)
		elif cmd == 'cache':
			wik_cache(wikipath)
		elif cmd == 'serve':
			import wikklytext.scripts.wikserve as ws
			ws.run_standalone(wikipath, opts.norespawn)
		elif cmd == 'conv':
			wik_conv(wikipath)
		elif cmd == 'makeboot':
			wik_makeboot(wikipath)
		elif cmd == 'trustall':
			wik_trustall(wikipath)
		elif cmd == 'updatemeta':
			wik_updatemeta(wikipath)
		elif cmd == 'gui':
			from wikklytext.scripts.wikgui import rungui
			rungui(opts.configpath)
		else:
			print "** Unknown command: %s" % cmd
		if cmd != 'serve':
			wikStore_Q.shutdown()
			sqliteQ.shutdown()
	except:
		# catch all errors and shutdown thread
		if cmd not in ['serve']:
			wikStore_Q.shutdown()
			sqliteQ.shutdown()
			
		raise
		
if __name__ == '__main__':
	main()
	
