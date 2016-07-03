from wikklytext import WikklyText_to_Tree, WikContext, load_wikitext
from wikklytext.serialize import dumpxml, cmpelem, loadxml
import unittest, os

class TestParser(unittest.TestCase):
	def doTest(self, name):
		name_in = os.path.join('testdata', '%s.txt' % name)
		name_out = os.path.join('testdata', '%s.xml' % name)
		
		context = WikContext(False)
		
		buf = load_wikitext(name_in)
		elemA = WikklyText_to_Tree(context, buf)
		if not os.path.isfile(name_out):
			# for test creation -- dump tree to stdout so it can be copied to "name.xml"
			print '\n',dumpxml(elemA)
		else:
			# if .xml exists, then run test and check results
			buf = open(name_out, 'rb').read()
			elemB = loadxml(buf)
			self.failIf(cmpelem(elemA,elemB) != True)

	def testMacroCalls(self):
		"Parsing of macro calls"
		for name in ['macro01', 'macro02', 'macro03', 'macro04', 'macro05', 'macro06']:
			self.doTest(name)

	def testLinks(self):
		"Parsing of links"
		for name in ['link01', 'link02', 'link03', 'link04']:
			self.doTest(name)

if __name__ == '__main__':
	unittest.main()
	
