import unittest, os, shutil
from wikklytext.port import *

class TestSearch(unittest.TestCase):
	def doSearchWords(self, store):
		from wikklytext.store import WikklyItem, WikklyQueryWords, WikklyQueryRegex
		
		# TW 2.3 comes with a non-empty storeArea, so delete any
		# existing items so I start with an empty store
		for item in store.getall():
			store.delete(item)
		
		self.failIf(len(store.names()))
		
		i = WikklyItem(u'With word One', 'Hello from One', [], 'Nobody')
		store.saveitem(i)
		
		i = WikklyItem(u'With word Two', 'Hello from Two', [], 'Nobody')
		store.saveitem(i)
		
		i = WikklyItem(u'With word Three', 'Hello from Three', [], 'Nobody')
		store.saveitem(i)
		
		i = WikklyItem(u'Subj Foo', 'Content Blah', [], 'Nobody')
		store.saveitem(i)
		
		i = WikklyItem(u'Subj Blah', 'Content Foo', [], 'Nobody')
		store.saveitem(i)
		
		i = WikklyItem(u'Subj AAA', 'Content BBB', ['CCC', 'DDD', 'EEE'], 'Nobody')
		store.saveitem(i)

		i = WikklyItem(u'Subj BBB', 'Content CCC', ['EEE', 'DDD', 'CCC'], 'Nobody')
		store.saveitem(i)
		
		# have to match over Subj+Content
		q = WikklyQueryWords(['With', 'Hello'], op_and=True)
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'With word One',u'With word Two',u'With word Three']))
		
		# restrict fields and search
		q = WikklyQueryWords(['Foo'], op_and=True, fields=['Name'])
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'Subj Foo']))

		q = WikklyQueryWords(['Foo'], op_or=True, fields=['Content'])
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'Subj Blah']))

		q = WikklyQueryWords(['CCC', 'DDD', 'EEE'], op_and=True, fields=['Tags'])
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'Subj AAA', u'Subj BBB']))

		# case sensitivity
		q = WikklyQueryWords(['hello'], op_and=True, no_case=False)
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(len(r))
		
		q = WikklyQueryWords(['hELlO'], op_and=True, no_case=True)
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'With word One',u'With word Two',u'With word Three']))
		
		# regex search
		q = WikklyQueryRegex(r'(One|Two|Three)')
		r = store.search(q)
		r = set_([item.name for item in r])
		self.failIf(r != set_([u'With word One',u'With word Two',u'With word Three']))
		
	def testFiles(self):
		from wikklytext.store import wikStore_files

		DIRNAME = 'testfolder'
		
		if os.path.isdir(DIRNAME):
			shutil.rmtree(DIRNAME)
		
		os.makedirs(DIRNAME)
		
		store = wikStore_files(DIRNAME)
		self.doSearchWords(store)

	def testSQLite(self):
		from wikklytext.store import wikStore_sqlite
		import os
		
		DBNAME = 'testsqlite.db'
		
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		store = wikStore_sqlite(DBNAME)
		self.doSearchWords(store)		

	def testStoreQ(self):
		from wikklytext.store.wikStore_Q import wikStore_Q, start, shutdown
		import os
		
		DBNAME = 'testQ.db'
		
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		start()
		store = wikStore_Q('sqlite', DBNAME)
		self.doSearchWords(store)	
		shutdown()

#	# uncached version
#	def do_U_TWTest(self, version):
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
#		self.doSearchWords(store)
#		
#	def testSearch_U_Tiddly20(self):
#		self.do_U_TWTest('2.0')
#		
#	def testSearch_U_Tiddly21(self):
#		self.do_U_TWTest('2.1')
#
#	def testSearch_U_Tiddly22(self):
#		self.do_U_TWTest('2.2')
#		
#	def testSearch_U_Tiddly23(self):
#		self.do_U_TWTest('2.3')
#	
#	def testSearch_U_Tiddly24(self):
#		self.do_U_TWTest('2.4')
		
	# cached version
	def do_C_TWTest(self, version):
		from wikklytext.store import wikStore_tw
		import wikklytext.base
		import shutil, os
		
		FILENAME = 'testtiddly_C%s.htm' % version
		
		if os.path.isfile(FILENAME):
			os.unlink(FILENAME)
			
		store = wikStore_tw(FILENAME, version)
		self.doSearchWords(store)
		
	def testSearch_C_Tiddly20(self):
		self.do_C_TWTest('2.0')
		
	def testSearch_C_Tiddly21(self):
		self.do_C_TWTest('2.1')

	def testSearch_C_Tiddly22(self):
		self.do_C_TWTest('2.2')

	def testSearch_C_Tiddly23(self):
		self.do_C_TWTest('2.3')

	def testSearch_C_Tiddly24(self):
		self.do_C_TWTest('2.4')

if __name__ == '__main__':
	unittest.main()

