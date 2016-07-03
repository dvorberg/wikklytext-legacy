# coding=utf-8

import unittest
from time import time
from wikklytext.port import *

class TestReadWrite(unittest.TestCase):
		
	def setUp(self):
		from wikklytext.store.wikStore_Q import start
		start()
		
	def tearDown(self):
		from wikklytext.store.wikStore_Q import shutdown
		# make sure thread is stopped even if an error occurs in the tests
		shutdown()
	
	def doStoreTests(self, store, content_type):
		from wikklytext.store import WikklyItem, WikklyDateTime
		
		now = WikklyDateTime()
		now.from_localtime()
		
		# TW 2.3 comes with a non-empty storeArea, so delete any
		# existing items so I start with an empty store
		for item in store.getall():
			store.delete(item)
			
		self.failIf(store.names() != [])
		
		itemA = WikklyItem(u'Item One', u'This is the first item',
						[u'items',u'one'], u'Frank', now, now,
						content_type)
		store.saveitem(itemA)
		self.failIf(set_(store.names()) != set_([u'Item One']))
		
		itemB = WikklyItem(u'Item Two', u'This is the second item',
						[u'items',u'two'], u'Frank', now, now,
						content_type)
		store.saveitem(itemB)
		self.failIf(set_(store.names()) != set_([u'Item One',u'Item Two']))
		
		# reload items & check
		loadA = store.getitem(u'Item One')
		self.failUnless(itemA == loadA)
		
		loadB = store.getitem(u'Item Two')
		self.failUnless(itemB == loadB)
		
		# replace 'Item Two' with 'Item Three'
		itemC = WikklyItem(u'Item Three', u'This is the third item',
						[u'items',u'three'], u'Frank', now, now,
						content_type)
		store.saveitem(itemC, u'Item Two')
		self.failIf(set_(store.names()) != set_([u'Item One',u'Item Three']))
		
		loadC = store.getitem(u'Item Three')
		self.failUnless(itemC == loadC)
		
		# API tests with oldname is set oddly
		itemD = WikklyItem(u'Item Four', u'This is the fourth item',
						[u'items',u'four'], u'Frank', now, now,
						content_type)
		# 'oldname' not existing should not crash
		store.saveitem(itemD, u'Item ZZZ')
		
		# ensure save still worked
		loadD = store.getitem(u'Item Four')
		self.failUnless(itemD == loadD)
		
		itemE = WikklyItem(u'Item Five', u'This is the fifth item',
						[u'items',u'five'], u'Frank', now, now,
						content_type)
		# oldname=newname (before newname exists) should be OK
		store.saveitem(itemE, u'Item Five')
		
		# ensure save still worked
		loadE = store.getitem(u'Item Five')
		self.failUnless(itemE == loadE)

		itemF = WikklyItem(u'Item Six', u'This is the sixth item',
						[u'items',u'six'], u'Frank', now, now,
						content_type)
		# oldname=newname and replacing newname
		store.saveitem(itemF, u'Item Five')
		
		# ensure save still worked
		loadF = store.getitem(u'Item Six')
		self.failUnless(itemF == loadF)
		
		# add an item with chars that need escaping
		itemG = WikklyItem(u'HTML escapes <div> </pre> \' " & &amp; &lt; &gt; \n', 
u"""
<div>
</div>
<pre>
</pre>
Not a newline: \\n
Quotes: " '
&lt; &gt; &lt;div&gt;
&Me""",
				[u'items',u'escapes'], u'Frank', now, now,
				content_type)
		
		store.saveitem(itemG)
		loadG = store.getitem(u'HTML escapes <div> </pre> \' " & &amp; &lt; &gt; \n')
		self.failUnless(itemG == loadG)

		itemH = WikklyItem(u'Multilingual, 世界你好, 안녕하세요, 여러분', 
u"""
"Hello world"
* ''Chinese'' 世界你好！
* ''Georgian'' სალამი მსოფლიოს!
* ''Greek'' Γεια σου, κόσμε!
* ''Korean'' 안녕하세요, 여러분!
""",
						[u'items',u'multilingual',u'世界你好 안녕하세요'], 
						u'Frank', now, now,
						content_type)
						
		store.saveitem(itemH)
		loadH = store.getitem(u'Multilingual, 世界你好, 안녕하세요, 여러분')
		self.failUnless(itemH == loadH)
		
		itemI = WikklyItem(u"HTML entities \u03a9 \u21d3", 
u"""
This item has known HTML entities that will be escaped.
* Dagger: \u2021
* Delta: \u0394
* Pi: \u03a0
* Suits: \u2663\u2666\u2665\u2660
""",
						[u'items',u'entities',u'\u2660 \u2666 \u2665 \u2660'], 
						u'Frank', now, now,
						content_type)
						
		store.saveitem(itemI)

		# check final list of names
		self.failIf(set_(store.names()) != \
			set_([u'Item One',u'Item Three',u'Item Four',u'Item Six',
			u'HTML escapes <div> </pre> \' " & &amp; &lt; &gt; \n',
			u'Multilingual, 世界你好, 안녕하세요, 여러분',
			u"HTML entities \u03a9 \u21d3"]))

		# now delete some of the items and check namelist
		store.delete(itemC)
		store.delete(itemH)
		store.delete(itemF)
		
		self.failIf(set_(store.names()) != \
			set_([u'Item One',u'Item Four',
			u'HTML escapes <div> </pre> \' " & &amp; &lt; &gt; \n',
			u"HTML entities \u03a9 \u21d3"]))
		
		# and with getall()
		names = set_([item.name for item in store.getall()])
		self.failIf(names != \
			set_([u'Item One',u'Item Four',
			u'HTML escapes <div> </pre> \' " & &amp; &lt; &gt; \n',
			u"HTML entities \u03a9 \u21d3"]))

		# create an item, shrink it by shortening a tag, then reloading.
		# errors can happen here if store fails to truncate old file prior
		# to writing new item since item has shrunk.
		itemJ = WikklyItem(u'itemJ', u'abcdefghi', tags=['aaabbbccc'])
		store.saveitem(itemJ)
		
		itemJ.tag_del('aaabbbccc')
		itemJ.tag_add('aaabbb')
		store.saveitem(itemJ)
		
		loadJ = store.getitem(u'itemJ')
		self.failIf(loadJ.content != u'abcdefghi')
		self.failIf(loadJ.tag_list() != [u'aaabbb'])
		
#	def doTiddlyWikiTest(self, version):
#		from wikklytext.store.wikStore_tw_re import wikStore_tw_re
#		import wikklytext.base
#		import shutil, os
#		
#		FILENAME = 'testtiddly%s.htm' % version
#		
#		if os.path.isfile(FILENAME):
#			os.unlink(FILENAME)
#			
#		store = wikStore_tw_re(FILENAME, version)
#		self.doStoreTests(store, u'TiddlyWiki')
#		
#	def testRWTiddly20(self):
#		self.doTiddlyWikiTest('2.0')
#		
#	def testRWTiddly21(self):
#		self.doTiddlyWikiTest('2.1')
#
#	def testRWTiddly22(self):
#		self.doTiddlyWikiTest('2.2')
#
#	def testRWTiddly23(self):
#		self.doTiddlyWikiTest('2.3')
#
#	def testRWTiddly24(self):
#		self.doTiddlyWikiTest('2.4')

	def doCachedTiddlyWikiTest(self, version):
		from wikklytext.store import wikStore_tw
		import wikklytext.base
		import shutil, os
		
		FILENAME = 'testtiddly_C%s.htm' % version
		
		if os.path.isfile(FILENAME):
			os.unlink(FILENAME)
			
		store = wikStore_tw(FILENAME, version)
		self.doStoreTests(store, u'TiddlyWiki')
		
	def testRWCachedTiddly20(self):
		self.doCachedTiddlyWikiTest('2.0')
		
	def testRWCachedTiddly21(self):
		self.doCachedTiddlyWikiTest('2.1')

	def testRWCachedTiddly22(self):
		self.doCachedTiddlyWikiTest('2.2')

	def testRWCachedTiddly23(self):
		self.doCachedTiddlyWikiTest('2.3')

	def testRWCachedTiddly24(self):
		self.doCachedTiddlyWikiTest('2.4')

	def testRWFiles(self):
		from wikklytext.store import wikStore_files
		import shutil, os
		
		DIRNAME = 'testfolder'
		
		if os.path.isdir(DIRNAME):
			shutil.rmtree(DIRNAME)
		
		os.makedirs(DIRNAME)
		
		store = wikStore_files(DIRNAME)
		self.doStoreTests(store, u'WikklyText')
		
	def testRWSQLite(self):
		from wikklytext.store import wikStore_sqlite
		import os
		
		DBNAME = 'testsqlite.db'
		
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		store = wikStore_sqlite(DBNAME)
		self.doStoreTests(store, u'WikklyText')		

	def testRW_Q(self):
		from wikklytext.store.wikStore_Q import wikStore_Q, start, shutdown
		import os
		
		DBNAME = 'testsqliteQ.db'
		
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		store = wikStore_Q('sqlite', DBNAME)
		self.doStoreTests(store, u'WikklyText')		
		
if __name__ == '__main__':
	unittest.main()
	
