
from wikklytext import WikklyItem
import os
from wikklytext.store.wikStore_Q import start, shutdown, wikStore_Q, WikStoreQError, StoreWorkerError
from wikklytext.store.wikStore_sqlite import wikStore_sqlite
from time import time
import unittest
from threading import Thread
from wikklytext.port import *

"""
test_store_rw tests wikStore_Q as well. All I need to test here is
to ensure threaded writing works.
"""

class TestQ(unittest.TestCase):
	def setUp(self):
		start()
		
	def tearDown(self):
		# make sure thread is stopped even if an error occurs in the tests
		shutdown()
		
	def testApi(self):
		"API test"
		# make sure errors are raised when thread not running
		shutdown()
		self.failUnlessRaises(WikStoreQError, wikStore_Q, 'sqlite', 'aaa')
		start()
		
	def testExc(self):
		"Ensure exceptions are passed up from worker thread"
		DBNAME = 'testQ.db'
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		store = wikStore_Q('sqlite', DBNAME)
		self.failUnlessRaises(StoreWorkerError, store.delete, 'aaa')
		
	def writer(self, store, names):
		for name in names:
			store.saveitem(WikklyItem(name, 'This is item "%s"' % name))
			
	def testWriting(self):
		"Multiple writers, single store."
		DBNAME = 'testQ.db'
		if os.path.isfile(DBNAME):
			os.unlink(DBNAME)
			
		store = wikStore_Q('sqlite', DBNAME)
		threads = []
		threads.append(Thread(target=self.writer, args=(store, ['aaa','bbb','ccc'])))
		threads.append(Thread(target=self.writer, args=(store, ['ddd','eee','fff'])))
		threads.append(Thread(target=self.writer, args=(store, ['ggg','hhh','iii'])))
		threads.append(Thread(target=self.writer, args=(store, ['jjj','kkk','lll'])))
		for t in threads:
			t.start()
			
		for t in threads:
			t.join()
		
		self.failUnless(set_(store.names()) == set_(['aaa','bbb','ccc','ddd','eee','fff','ggg','hhh','iii',
							'jjj','kkk','lll']))
		
	def testMulti(self):
		"Multiple stores with one writer each."
		DB1 = 'testQA.db'
		DB2 = 'testQB.db'
		DB3 = 'testQC.db'
		if os.path.isfile(DB1): os.unlink(DB1)
		if os.path.isfile(DB2): os.unlink(DB2)
		if os.path.isfile(DB3): os.unlink(DB3)
			
		store1 = wikStore_Q('sqlite', DB1)
		store2 = wikStore_Q('sqlite', DB2)
		store3 = wikStore_Q('sqlite', DB3)
		threads = []
		threads.append(Thread(target=self.writer, args=(store1, ['aaa','bbb','ccc'])))
		threads.append(Thread(target=self.writer, args=(store2, ['ddd','eee','fff'])))
		threads.append(Thread(target=self.writer, args=(store3, ['ggg','hhh','iii'])))
		for t in threads:
			t.start()
			
		for t in threads:
			t.join()
		
		self.failUnless(set_(store1.names()) == set_(['aaa','bbb','ccc']))
		self.failUnless(set_(store2.names()) == set_(['ddd','eee','fff']))
		self.failUnless(set_(store3.names()) == set_(['ggg','hhh','iii']))
		
if __name__ == '__main__':
	unittest.main()

