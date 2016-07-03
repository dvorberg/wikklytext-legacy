import unittest

class TestHTML(unittest.TestCase):
	
	def testescapes(self):
		from wikklytext.store.wikStore_tw_re import escape_html_entities, unescape_html_dentities
		cases = [
			u" no entities ",
			# NOT at start & end
			u"abc &#187; def &#160;&#8217; ghi",
			# entities at start & end
			u"&#160;abc &#187; def &#160;&#8217; ghi&#160;",
			]
			
		for s in cases:
			s2 = unescape_html_dentities(s)
			s3 = escape_html_entities(s2)
			self.failIf(s3 != s)
			
	def testTagSplit(self):
		from wikklytext.store import tags_split
		s = 'aaa bbb ccc  ddd \t eee \t  fff'
		self.failIf(tags_split(s) != ['aaa','bbb','ccc','ddd','eee','fff'])
		s = 'aaa bbb \t [[ccc ddd]] eee \t [[fff ggg]] hhh'
		self.failIf(tags_split(s) != ['aaa','bbb','ccc ddd','eee','fff ggg','hhh'])
		
	def testTagsJoin(self):
		from wikklytext.store import tags_join
		tags = ['aaa','bbb','ccc']
		self.failIf(tags_join(tags) != u'aaa bbb ccc')
		tags = ['aaa','bbb ccc',' ddd','eee ','\tfff','ggg']
		self.failIf(tags_join(tags) != u'aaa [[bbb ccc]] [[ ddd]] [[eee ]] [[\tfff]] ggg')

if __name__ == '__main__':
	unittest.main()

