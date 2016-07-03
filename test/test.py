"""
Convenient way to run all tests.

You can also run individual tests like:
	 python test_store.py
"""
import os

# run my from folder
p,n = os.path.split(__file__)
if len(p):
	os.chdir(p)
	
import unittest

def suite():
	import test_store_rw, test_store_esc, test_store_search, test_store_q,	\
			test_datetime, test_camel, test_stress_stores, test_parser
	suite = unittest.TestSuite()

	# this is a little weird to be compatible with Python 2.3
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_store_rw)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_store_esc)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_store_search)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_store_q)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_datetime)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_camel)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_stress_stores)._tests)
	suite.addTests(unittest.TestLoader().loadTestsFromModule(test_parser)._tests)
	
	return suite
	
unittest.TextTestRunner(verbosity=2).run(suite())


