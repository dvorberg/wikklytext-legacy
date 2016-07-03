import unittest
from wikklytext.store.wikStore import WikklyDateTime
import datetime as DT

class TestDateTime(unittest.TestCase):
	def testParseUTC(self):
		# pairs are: (input_UTC, output_UTC) where "output_UTC"
		# is the corrected version of input_UTC)
		pairs = [
			# ok format, no errors
			('200802271234', '200802271234'),
			# Feb 14 2008 with wrong hours (Feb 12 2008 48:23)
			('200802124823', '200802140023'),
			# Feb 10 2008 with wrong day (Jan 41 2008)
			('200801410432', '200802100432'),
			# Jan 12 2008 with wrong year/day (Dec 43 2007)
			('200712430543', '200801120543'),
			]
			
		for a,b in pairs:
			wdt = WikklyDateTime()
			wdt.from_store(a)
			# converting back to_store fixes any errors
			self.failIf(b != wdt.to_store())
			
	def testLocaltime(self):
		now = DT.datetime.now()
		# zero out seconds and usec since those are not stored
		now = DT.datetime(now.year, now.month, now.day, now.hour, now.minute)
		#print now
		wdt = WikklyDateTime()
		wdt.from_localtime(now)
		#print wdt.to_store()
		self.failIf(now != wdt.to_localtime())

	def testFileTimes(self):
		import os, stat
		st = os.stat('test_datetime.py')
		ctime = st[stat.ST_CTIME]
		mtime = st[stat.ST_MTIME]
		
		wdt = WikklyDateTime()
		wdt.from_file_ctime('test_datetime.py')
		self.failIf(DT.datetime.fromtimestamp(ctime) != wdt.to_localtime())
		
		wdt.from_file_mtime('test_datetime.py')
		self.failIf(DT.datetime.fromtimestamp(mtime) != wdt.to_localtime())
		
	def testYMD(self):
		now = DT.datetime.now()
		wdt = WikklyDateTime(from_localtime=now)
		self.failIf(('%4d%02d%02d' % (now.year, now.month, now.day)) != wdt.to_YMD())

	def test822(self):
		now = DT.datetime(2008, 3, 8, 15, 20, 32)
		wdt = WikklyDateTime()
		wdt.from_utc(now)
		self.failUnless(wdt.to_rfc822() == 'Sat, 08 Mar 2008 15:20:32 +0000')
		
if __name__ == '__main__':
	unittest.main()

