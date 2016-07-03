from wikklytext.store import wikStore_tw, WikklyItem, wikStore_sqlite
import sys, os
import unittest

NAME = 'stressout'
NR_PROCESSES = 4
ITEMS_PER_WRITER = 10

def write_items_TW_A(basename, nr):
	# use same store object for all writes
	store = wikStore_tw(NAME+'.html')
	for i in range(nr):
		w = WikklyItem('%s-%d' % (basename,i), '%s item #%d (A)' % (basename,i))
		store.saveitem(w)

def write_items_TW_B(basename, nr):
	# use new store object for each write
	for i in range(nr):
		store = wikStore_tw(NAME+'.html')
		w = WikklyItem('%s-%d' % (basename,i), '%s item #%d (B)' % (basename,i))
		store.saveitem(w)

def write_items_SQL_A(basename, nr):
	# use same store object for all writes
	store = wikStore_sqlite(NAME+'.db')
	for i in range(nr):
		w = WikklyItem('%s-%d' % (basename,i), '%s item #%d (A)' % (basename,i))
		store.saveitem(w)

def write_items_SQL_B(basename, nr):
	# use new store object for each write
	for i in range(nr):
		store = wikStore_sqlite(NAME+'.db')
		w = WikklyItem('%s-%d' % (basename,i), '%s item #%d (B)' % (basename,i))
		store.saveitem(w)

# different ways to run
def run_processes_TW_A():
	procs = [os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, __file__, 'wTA', 'AnItem%d' % i]) \
				for i in range(NR_PROCESSES)]
	for p in procs:
		os.waitpid(p, 0)
		
def run_processes_TW_B():
	procs = [os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, __file__, 'wTB', 'AnItem%d' % i]) \
				for i in range(NR_PROCESSES)]
	for p in procs:
		os.waitpid(p,0)

def run_processes_SQL_A():
	procs = [os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, __file__, 'wSA', 'AnItem%d' % i]) \
				for i in range(NR_PROCESSES)]
	for p in procs:
		os.waitpid(p,0)

def run_processes_SQL_B():
	procs = [os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, __file__, 'wSB', 'AnItem%d' % i]) \
				for i in range(NR_PROCESSES)]
	for p in procs:
		os.waitpid(p,0)

class StoreStresser(unittest.TestCase):
	def testTiddlyWiki_A(self):
		if os.path.isfile(NAME+'.html'):
			os.unlink(NAME+'.html')
			
		run_processes_TW_A()	
		
		store = wikStore_tw(NAME+'.html')
		names = store.names()
		#print "%d names (expect %d)" % (len(names),NR_PROCESSES * ITEMS_PER_WRITER)
		#print names
		
		self.failIf(len(names) != NR_PROCESSES * ITEMS_PER_WRITER)
	
	def testTiddlyWiki_B(self):
		if os.path.isfile(NAME+'.html'):
			os.unlink(NAME+'.html')
			
		run_processes_TW_B()	
		
		store = wikStore_tw(NAME+'.html')
		names = store.names()
		#print "%d names (expect %d)" % (len(names),NR_PROCESSES * ITEMS_PER_WRITER)
		#print names
		
		self.failIf(len(names) != NR_PROCESSES * ITEMS_PER_WRITER)
		
	def testSQLite_A(self):
		if os.path.isfile(NAME+'.db'):
			os.unlink(NAME+'.db')
			
		run_processes_SQL_A()	
		
		store = wikStore_sqlite(NAME+'.db')
		names = store.names()
		#print "%d names (expect %d)" % (len(names),NR_PROCESSES * ITEMS_PER_WRITER)
		#print names
		
		self.failIf(len(names) != NR_PROCESSES * ITEMS_PER_WRITER)
	
	def testSQLite_B(self):
		if os.path.isfile(NAME+'.db'):
			os.unlink(NAME+'.db')
			
		run_processes_SQL_B()	
		
		store = wikStore_sqlite(NAME+'.db')
		names = store.names()
		#print "%d names (expect %d)" % (len(names),NR_PROCESSES * ITEMS_PER_WRITER)
		#print names
		
		self.failIf(len(names) != NR_PROCESSES * ITEMS_PER_WRITER)
		
# how should I run?
if __name__ == '__main__':
	if len(sys.argv) == 1:
		unittest.main()
		
	elif len(sys.argv) == 2 and sys.argv[1] == 'm':
		unittest.main()
		
	elif len(sys.argv) == 3 and sys.argv[1] == 'wTA':
		write_items_TW_A(sys.argv[2], ITEMS_PER_WRITER)
	
	elif len(sys.argv) == 3 and sys.argv[1] == 'wTB':
		write_items_TW_B(sys.argv[2], ITEMS_PER_WRITER)
	
	elif len(sys.argv) == 3 and sys.argv[1] == 'wSA':
		write_items_SQL_A(sys.argv[2], ITEMS_PER_WRITER)
	
	elif len(sys.argv) == 3 and sys.argv[1] == 'wSB':
		write_items_SQL_B(sys.argv[2], ITEMS_PER_WRITER)
		
	else:
		print "BAD ARGS",sys.argv
	
