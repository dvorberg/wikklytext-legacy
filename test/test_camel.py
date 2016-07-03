import unittest
from wikklytext.wikwords import camelpair

class CamelTest(unittest.TestCase):
	def testCamelPairs(self):
		for text,Word,Fragment,Remainder in [
			('CamelWord non camel text AbcDef', 'CamelWord', ' non camel text ', 'AbcDef'),
			('CamelWord non camel text', 'CamelWord', ' non camel text', ''),
			('CamelWord', 'CamelWord', '', ''),
			('abcdef CamelWord', '', 'abcdef ', 'CamelWord'),
			('abcdef', '', 'abcdef', ''),
			('ABC', '', 'ABC', ''),
			('ABC CamelWord', '', 'ABC ', 'CamelWord'),
			('abcDefGhi Abc', '', 'abcDefGhi ', 'Abc'),
			]:
			#print "TEXT",text
			#print "EXPECT W,F,R",repr(Word),repr(Fragment),repr(Remainder)
			remainder, word, fragment = camelpair(text)
			#print "GOT W,F,R", repr(word), repr(fragment), repr(remainder)
			self.failIf(remainder != Remainder)
			self.failIf(word != Word)
			self.failIf(fragment != Fragment)
			
if __name__ == '__main__':
	unittest.main()


