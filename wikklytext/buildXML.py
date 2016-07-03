"""
wikklytext.buildXML.py: Rendering of WikklyText to XML. Part of the WikklyText suite.

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

#import elementtree.ElementTree as etree
from wikklytext.parser import WikklyBaseContentParser
import re
from wikklytext.base import StringIO, WikError, xmltrace, ifelse, Text, \
				ElementTree, Element, SubElement, ElementList
import wikklytext.coremacros
from urlparse import urlparse
from wikklytext.util import xml_escape, xmlhead, deprecation
from wikklytext.eval import eval_wiki_text
from wikklytext.serialize import dumpxml
		
class WikklyContentToXML(WikklyBaseContentParser):
	
	# There are several kinds of Text:
	#   Text = Escape &, <, >, and \n
	#   TextCode = Above plus escape spaces & tabs to preserve spacing
	#   TextHTML = Escape nothing (raw HTML)
	#   TextNoWiki = For <nowiki> (escaped like Text)
	#   TextPyCode = Text of <?py code
	#
	# tag_to_texttag maps a parent tag to the Text* tag it uses.
	# If a tag is not listed here, it gets 'Text' (normal escaping).
	tag_to_texttag = {
		'CodeBlock': 'TextCode',
		'CodeInline': 'TextCode',
		'ErrorMessage': 'TextCode',
		'ErrorLookingAt': 'TextCode',
		'ErrorTrace': 'TextCode',
		'RawHTML': 'TextHTML',
		'NoWiki': 'TextNoWiki',
		'PyCode': 'TextPyCode',
		}

	any_text_tag = ('Text', 'TextCode', 'TextHTML', 'TextNoWiki', 'TextPyCode')
	
	def __init__(self):
		self.parent_stack = []
		self.errors_list = []
		
	def set_context(self, wcontext):
		self.context = wcontext
		
	def cur_text_tag(self):
		"What Text* tag should be used for current node?"
		if self.curnode.tag in self.any_text_tag:
			return self.tag_to_texttag.get(self.parent_stack[-1].tag, 'Text')
		else:
			return self.tag_to_texttag.get(self.curnode.tag, 'Text')
			
	def default_base_url(self):
		"Returns $BASE_URL as text, WITH trailing /"
		url = self.context.var_get_text('$BASE_URL')
		
		# ensure trailing /
		if len(url) and url[-1] != '/':
			url = url + '/'
					
		return url

	def get_site_url(self):
		"Returns $SITE_URL as text, WITHOUT trailing /"
		url = self.context.var_get_text('$SITE_URL')
		
		# ensure no trailing /
		if len(url) and url[-1] == '/':
			url = url[:-1]
			
		return url
		
	def makenew(self):
		"Make a new parser like this one."
		p = WikklyContentToXML()
		p.set_context(self.context)
		return p
		
	def beginDoc(self):
		self.rootnode = Element("WikklyContent")
		self.curnode = self.rootnode
		# collect all errors under this element - mixing them with
		# content can cause problems
		self.pushnew('ErrorsList')
		self.popnode('ErrorsList')
		# content goes here
		self.pushnew('Content')
		
	def endDoc(self):
		# make sure there is at least one node under <Content>
		node = self.rootnode.find('Content')
		if len(node) == 0:
			# add an empty Text node, simplifies other code
			# to always have at least one node under <Content>
			node.append(Text(""))
			
	def getInnerResult(self):
		"""
		Returns 'inner' result, that is, the subnodes of the <Content> node,
		as an ElementList.
		"""
		outnode = ElementList()
		for node in self.rootnode.find('Content'):
			outnode.append(node)
			
		return outnode

	def getErrors(self):
		"Return current error list, in same format that 'addParserErrors' accepts."
		errors = self.rootnode.find('ErrorsList')
		if errors is None:
			return ElementList('ErrorsList')
		else:
			return errors

	def addElement(self, element):
		"When you have an already-created Element (like from a macro call) add it here."
		if self.curnode.tag in self.any_text_tag:
			# Text nodes have no children, really want to add to parent
			self.curnode = self.parent_stack.pop()
			
		self.curnode.append(element)		
		
	def addParserErrors(self, errors):
		errlist = self.rootnode.find('ErrorsList')
		
		for node in errors:
			errlist.append(node)
			
	def getRoot(self):
		"""
		Get root node of generated tree.
		"""
		return self.rootnode
		
	def getXML(self, encoding):
		"""
		Get result as XML.
		
		encoding = Specifies encoding.
		"""
		return dumpxml(self.rootnode)
		
	def pushnew(self, tag):
		"Make new node 'tag' as a child of self.curnode - self.curnode is pushed to stack."
		if self.curnode.tag in self.any_text_tag:
			# Text nodes have no children, really want to add to parent
			self.curnode = self.parent_stack.pop()
		
		self.parent_stack.append(self.curnode)
		self.curnode = SubElement(self.curnode, tag)
		
	def popto(self, tag):
		"""
		Pop until tag is in .curnode.
		"""
		# if inside Text, pop
		if self.curnode.tag in self.any_text_tag:
			self.curnode = self.parent_stack.pop()
			
		# if .tag NOT next on stack, then there has been a nesting error
		if self.curnode.tag != tag:
			msg = "NESTING ERROR, trying to pop %s, found %s\n" % (tag, self.curnode.tag)
			msg += "Stack from parent:\n"
			msg += dumpxml(self.parent_stack[-1])
			self.error(msg)
			return
			
	def popnode(self, tag):
		"""
		Finishes node tagged 'tag' and sets self.curnode to its parent.
		"""
		# pop till tag is curnode
		self.popto(tag)
			
		self.curnode = self.parent_stack.pop()
		
	def pushpop(self, tag):
		"Push new node under curnode and immediately pop it off"
		self.pushnew(tag)
		self.popnode(tag)
		
	def findup(self, tag):
		"""
		Look upwards in parent stack to find tag. Returns Element or None if not found.
		Does not modify stack or curnode.
		"""
		for i in range(len(self.parent_stack)):
			node = self.parent_stack[-1*(i+1)]
			if node.tag == tag:
				return node
				
		return None
		
	def getup(self):
		"Get first non-Text* parent in stack."
		i = -1
		while self.parent_stack[i].tag in self.any_text_tag:
			i -= 1
			
		return self.parent_stack[i]
		
	def beginBold(self): self.pushnew('Bold')	
	def endBold(self): self.popnode('Bold')
	
	def beginItalic(self): self.pushnew('Italic')	
	def endItalic(self): self.popnode('Italic')

	def beginStrikethrough(self): self.pushnew('Strikethrough')
	def endStrikethrough(self): self.popnode('Strikethrough')
	
	def beginUnderline(self): self.pushnew('Underline')
	def endUnderline(self): self.popnode('Underline')
	
	def beginSuperscript(self): self.pushnew('Superscript')
	def endSuperscript(self): self.popnode('Superscript')

	def beginSubscript(self): self.pushnew('Subscript')
	def endSubscript(self): self.popnode('Subscript')

	def beginHighlight(self, style=None):
		# supported highlight styles:
		#	1. @@text@@ - (style=None) - Apply standard highlight
		#   2. @@prop1: style one; prop2: style two; ... ; items@@ - Apply given style to items.
		#   3. @@color(color): ...@@ - Apply color
		#   4. @@bgcolor(color): .. @@ - Apply background color
	
		self.pushnew('Highlight')
		if style is not None:
			# try parsing case #2 (sync w/wikklytext.lexer:t_HIGHLIGHT_CSS)
			#m2 = re.match('@@((\s*[a-zA-Z]\S+\s*:\s*\S+\s*;)+)', style)
			m2 = re.match('@@((\s*[a-zA-Z][a-zA-Z0-9-]*\s*:.+?;)+)', style)
			             
			# case #3
			m3 = re.match(r'@@color\((.+?)\):', style)
			
			# case #4
			m4 = re.match('@@bgcolor\((.+?)\):', style)
			
			# set style info into Highlight node; place text in Text under it
			
			if m2:
				# @@prop1: style1; prop2: style2; ... ;
				style = m2.group(1)				
			elif m3:
				# @@color(..): ... @@
				style = "color: %s;" % m3.group(1)				
			elif m4:
				# @@bgcolor(..): ... @@
				style = "background: %s;" % m4.group(1)							
			else:
				raise WikError("Unknown style: %s" % repr(style))
				
			if style is not None:
				self.curnode.set('style', style)
				
	def endHighlight(self):
		self.popnode('Highlight')
		
	def beginNList(self): self.pushnew('NumberedList')		
	def endNList(self): self.popnode('NumberedList')
		
	def beginNListItem(self, marker):
		nr = len(marker)
		if nr > 6:
			nr = 6
			
		self.pushnew('NumberedListItem')
		self.curnode.set('level', '%d' % nr)
		
	def endNListItem(self):
		self.popnode('NumberedListItem')
		
	def beginUList(self):
		self.pushnew('UnnumberedList')
		
	def endUList(self):
		self.popnode('UnnumberedList')
		
	def beginUListItem(self, marker):
		nr = len(marker)
		if nr > 6:
			nr = 6
			
		self.pushnew('UnnumberedListItem')
		self.curnode.set('level', '%d' % nr)
		
	def endUListItem(self):
		self.popnode('UnnumberedListItem')

	def beginHeading(self, level):
		self.pushnew('Heading')
		# max 6 levels
		if level > 6:
			level = 6
			
		self.curnode.set('level', '%d' % level)
		
	def endHeading(self):
		self.popnode('Heading')
			
	def beginBlockIndent(self):
		self.pushnew('BlockIndent')
		
	def endBlockIndent(self):
		self.popnode('BlockIndent')
		
	def beginLineIndent(self):
		self.pushnew('LineIndent')
		
	def endLineIndent(self):
		self.popnode('LineIndent')

	def handleLink(self, A, B=None):
		"""
		Forms accepted here:
			[[A|B]]
			[[A]]
			
		Which expands to a full list of forms:
			[[SourceText|DestText]] -> link to Dest (URL, item, etc.)
			[[SourceText|#Anchor]]  -> link to anchor
			[[#Anchor]]             -> create anchor
			[[DestText]]            -> link where SourceText = DestText
			
		SourceText and DestText are stored as-is -- resolution to final URLs
		is done during tree evaluation.
		"""
		# [[A]] forms
		if B is None:
			# [[#Anchor]]
			if A[0] == '#':
				self.pushnew('CreateAnchor')
				self.characters(A[1:]) # remove leading '#'
				self.popnode('CreateAnchor')
			# [[DestText]]
			else:
				self.pushnew('Link')
				self.pushnew('LinkSource')
				self.characters(A)
				self.popnode('LinkSource')
				self.popto('Link')
				self.pushnew('LinkDest')
				self.characters(A)
				self.popnode('LinkDest')
				self.popnode('Link')
		# [[A|B]] forms
		else:
			self.pushnew('Link')
			self.pushnew('LinkSource')
			self.characters(A)
			self.popnode('LinkSource')
			self.popto('Link')
			self.pushnew('LinkDest')
			self.characters(B)
			self.popnode('LinkDest')
			self.popnode('Link')
				
	def handleImgLink(self, title, filename, url):
		self.pushnew('Image')
		
		if title is not None:
			self.pushnew('ImageTitle')
			self.characters(title)
			self.popnode('ImageTitle')
			
		if url is not None:
			self.pushnew('ImageLink')
			self.characters(url)
			self.popnode('ImageLink')
			
		self.pushnew('ImageFilename')
		self.characters(filename)
		self.popnode('ImageFilename')
		
		self.popnode('Image')
						
	def beginCodeBlock(self):
		self.pushnew('CodeBlock')
		
	def endCodeBlock(self):
		self.popnode('CodeBlock')
		
	def beginCodeInline(self):
		self.pushnew('CodeInline')
		
	def endCodeInline(self):
		self.popnode('CodeInline')
	
	def beginTable(self):
		self.pushnew('Table')
		
	def endTable(self):
		self.popto('Table')
		# if there is a caption, it must be the first tag after <Table>, so
		# find and move it if needed
		caption = self.curnode.find('TableCaption')
		if caption is not None:
			self.curnode.remove(caption)
			self.curnode.insert(0, caption)
			
		self.popnode('Table')
		
	def setTableCaption(self, txt):
		# self-closing, just make a Text node holding caption
		self.pushnew('TableCaption')
		self.characters(txt)
		self.popnode('TableCaption')
		
	def beginTableRow(self):
		self.pushnew('TableRow')
		
	def endTableRow(self):
		self.popto('TableRow')
		
		# iterate over TableCells and set colspans
		span = 1
		for cell in self.curnode:
			if self.cell_is_colskip(cell):
				span += 1
			else:
				if span > 1: # don't show 'colspan=1' - too verbose
					cell.set('colspan', '%d' % span)
					span = 1
	
		# iterate over TableCells and set rowspans
		for (i,cell) in enumerate(self.curnode):
			# find a cell with '~' then scan upwards and rowspan+=1 on first non-'~' cell
			if not self.cell_is_rowskip(cell):
				continue
				
			# get ith column
			column = self.get_table_column(i)
			column.reverse() # I am now the 0th item
			# find first cell that's not a rowskip
			for icell in column[1:]:
				if icell is None:
					continue # skip missing columns
					
				if not self.cell_is_rowskip(icell):
					n = int(icell.get('rowspan','1'))
					icell.set('rowspan', '%d' % (n+1))
					break
					
		self.popnode('TableRow')
	
	def beginTableCell(self):
		self.pushnew('TableCell')
		
	def is_header_cell(self, node):
		"Is this TableCell a header cell?"
		txt = self.cell_leading_text(node).lstrip()
		return (len(txt) and txt[0] == '!')
	
	def cell_strip_heading_char(self, node):
		"Strip ! from leading text in cell."
		txt = self.cell_leading_text(node)
		m = re.match('(\s*)[\!]+(.*)', txt)
		if m:
			txt = m.group(1) + m.group(2)
			self.set_cell_leading_text(node, txt)
			
	def cell_leading_text(self, node):
		"Return leading text from cell, or '' if no Text node at start."
		if len(node) and node[0].tag == self.cur_text_tag():
			return node[0].text
		else:
			return ''
		
	def set_cell_leading_text(self, node, text):
		if len(node) and node[0].tag == self.cur_text_tag():
			node[0].text = text
		else:
			# no existing Text*, insert one
			sub = Element(self.cur_text_tag())
			sub.text = text
			node.insert(0, sub)
			
	def cell_trailing_text(self, node):
		"Return trailing text from cell, or '' if no Text node at end."
		if len(node) and node[-1].tag == self.cur_text_tag():
			return node[-1].text
		else:
			return ''
		
	def get_cell_alignment(self, node):
		"Calculate text alignment for TableCell node. Returns 'left', 'center', or 'right'"
		head = self.cell_leading_text(node)
		tail = self.cell_trailing_text(node)
		headsp = ifelse(re.match('^\s+', head), True, False)
		tailsp = ifelse(re.match('.*\s+$', tail), True, False)
		if self.is_header_cell(node):
			# per tiddlywiki, nospace == center justify (for headers)
			if (not headsp and not tailsp) or (headsp and tailsp):
				return 'center'
			elif not headsp and tailsp:
				return 'left'
			else:
				return 'right'
		else:
			# per tiddlywiki, nospace == left justify (for data cells)
			if headsp and tailsp:
				return 'center'
			elif (not headsp and tailsp) or (not headsp and not tailsp):
				return 'left'
			else:
				return 'right'

	def cell_is_colskip(self, node):
		"Is TableCell a column skip ('>')?"
		# must have a single Text subnode and exactly '>' as text
		return (len(node) == 1 and node[0].tag == self.cur_text_tag() and node[0].text == '>')
		
	def cell_is_rowskip(self, node):
		"Is TableCell a row skip ('~')?"
		# must have a single Text subnode and exactly '~' as text
		return (len(node) == 1 and node[0].tag == self.cur_text_tag() and node[0].text == '~')

	def get_table_column(self, i):
		"""
		Get the i'th column as a list of TableCells. Some entries may be None if there
		are short rows in the table.
		
		NOTE: curnode must be somewhere inside the Table when calling this.
		"""
		collist = []
		table = self.findup('Table')
		for row in table:
			try:
				collist.append(row[i])
			except IndexError:
				collist.append(None) # short row - add None

		return collist
	
	def endTableCell(self):
		# bring TableCell back to self.curnode
		self.popto('TableCell')

		# look for bgcolor() in leading text (do this BEFORE other calcs)
		text = self.cell_leading_text(self.curnode)
		m = re.match(r'\s*bgcolor\((.+?)\):(\s*.*?\s*)$', text)
				
		# did I get bgcolor()
		if m:
			self.curnode.set('bgcolor', m.group(1))
			self.set_cell_leading_text(self.curnode, m.group(2))
					
		if self.is_header_cell(self.curnode):
			self.curnode.set('type', 'header')
		else:
			self.curnode.set('type', 'data')
			
		self.curnode.set('text-align', self.get_cell_alignment(self.curnode))
		
		# remove leading '!' now that I've calculated type & alignment
		self.cell_strip_heading_char(self.curnode)
		
		# skipped cell?
		if self.cell_is_colskip(self.curnode) or self.cell_is_rowskip(self.curnode):
			self.curnode.set('skip', '1')
		
		# TableCell done
		self.popnode('TableCell')
	
	# General note on DefinitionList: Even though it doesn't matter for HTML
	# rendering, I make sure here that the XML is well-formed, inserting missing
	# term/definitions as needed.
	def beginDefinitionList(self):
		self.pushnew('DefinitionList')
		self.pushnew('DefinitionEntry')
		
	def endDefinitionList(self):
		# watch for missing definition at end
		self.popto('DefinitionEntry')
		if len(self.curnode) == 1:
			# add empty def
			self.pushpop('DefinitionDef')
			
		self.popnode('DefinitionEntry')
		self.popto('DefinitionList')
		# check for empty entry at end
		entry = self.curnode[-1]
		if not len(entry):
			self.curnode.remove(entry)
			
		self.popnode('DefinitionList')
		
	def beginDefinitionTerm(self):
		# if current DefinitionEntry already has one subnode, then
		# I have a lone term missing a definition. add empty definition
		# and make new empty element first.
		if len(self.curnode) == 1:
			self.pushnew('DefinitionDef')
			self.popnode('DefinitionDef')
			self.popnode('DefinitionEntry')
			self.pushnew('DefinitionEntry')
			
		self.pushnew('DefinitionTerm')
		
	def endDefinitionTerm(self):
		self.popnode('DefinitionTerm')
		
	def beginDefinitionDef(self):
		# if current DefinitionEntry has no subnodes, then the term is
		# missing. add empty term first.
		if len(self.curnode) == 0:
			self.pushpop('DefinitionTerm')
			
		self.pushnew('DefinitionDef')
		
	def endDefinitionDef(self):
		self.popnode('DefinitionDef')
		self.popnode('DefinitionEntry')
		self.pushnew('DefinitionEntry')
		
	def beginCSSBlock(self, classname):
		self.pushnew('CSSBlock')
		# classname is safe (see lexer): [a-zA-Z_-]
		self.curnode.set('class', classname)
		
	def endCSSBlock(self):
		self.popnode('CSSBlock')
		
	def beginRawHTML(self):
		self.pushnew('RawHTML')
		
	def endRawHTML(self):
		# should have: <RawHTML><TextHTML> ... </TextHTML></RawHTML>
		# remove the 'RawHTML' tag, promoting the TextHTML. (<RawHTML> was
		# only needed in order to create the correct type of <Text> node.
		# Can discard now since <TextHTML> captures everything.)
		self.popto('RawHTML')
		
		# sanity
		if len(self.curnode) != 1 or self.curnode[0].tag != 'TextHTML':
			raise WikError("Internal error - bad nodes under <RawHTML>")
		
		rawnode = self.curnode
		txt = self.curnode[0]
		
		self.popnode('RawHTML')
		self.curnode.remove(rawnode)
		self.curnode.append(txt)
		
	def beginNoWiki(self):
		self.pushnew('NoWiki')
		
	def endNoWiki(self):
		# like RawHTML, remove <NoWiki>, leaving TextNoWiki
		self.popto('NoWiki')
		
		# sanity
		if len(self.curnode) != 1 or self.curnode[0].tag != 'TextNoWiki':
			raise WikError("Internal error - bad nodes under <NoWiki>")
		
		rawnode = self.curnode
		txt = self.curnode[0]
		
		self.popnode('NoWiki')
		self.curnode.remove(rawnode)
		self.curnode.append(txt)
	
	def beginPyCode(self):
		self.pushnew('PyCode')
		
	def endPyCode(self):
		self.popnode('PyCode')
		
	def separator(self):
		self.pushpop('Separator')
		
	def EOLs(self, txt):
		if self.context.var_get_int('$REFLOW'):
			if len(txt) > 1:
				self.pushnew('BlankLines')
				self.curnode.set('count', '%d' % (len(txt)-1))
				self.popnode('BlankLines')
			else:
				self.characters(' ')
		else:
			for i in range(len(txt)):
				self.linebreak()
			
	def linebreak(self):
		self.pushpop('LineBreak')
		
	def dash(self):
		self.pushpop('DashChar')
		
	def characters(self, txt):
		if self.curnode.tag not in self.any_text_tag:
			# start correct type of Text* tag based on parent content type
			self.pushnew(self.cur_text_tag())
			self.curnode.text = ''
			
		self.curnode.text += txt
	
	def error(self, message, looking_at=None, trace=None):
		self.pushnew('Error')
		
		if len(message):
			self.pushnew('ErrorMessage')
			self.characters(message)
			self.popnode('ErrorMessage')
			
		if looking_at is not None and len(looking_at):
			self.pushnew('ErrorLookingAt')
			self.characters(looking_at)
			self.popnode('ErrorLookingAt')
			
		if trace is not None and len(trace):
			self.pushnew('ErrorTrace')
			self.characters(trace)
			self.popnode('ErrorTrace')
			
		self.popto('Error')
		node = self.curnode
		self.popnode('Error')
		self.curnode.remove(node)
		elist = self.rootnode.find('ErrorsList')
		elist.append(node)

def WikklyText_to_Tree(wcontext, wikitext): 
	"""
	;wcontext
	:A ~WikContext; you should initialize the following attributes: <<echo '''
		* .restricted_mode
		* .max_runtime
		* .rendercache
		* set any desired user/system vars via var_set_int() or var_set_text()
	'''>>|
	;wikitext
	:The wiki formatted text to parse.
	
	Returns the root Element of the parsed tree. Note that the returned tree will
	be in raw parsed form -- call eval.eval_wiki_elem() to finalize it.
	"""
	from wikklytext.eval import parse_wiki_text
	
	parser = WikklyContentToXML()
	wcontext.parser = parser
	parser.set_context(wcontext)	
	
	parser.beginDoc()
	elem = parse_wiki_text(wcontext, wikitext)
	parser.addElement(elem)
	parser.endDoc()
	
	return parser.getRoot()
	
def WikklyText_to_XML(content, encoding, safe_mode, setvars=None, 
						max_runtime=-1, url_resolver=None,
						tree_posthook=None, plugin_dirs=None, 
						rendercache=None, macro_handler=None, **kwargs):
	"""
	Convert the given wikitext to XML.
	
	|>|!Inputs|
		|content\
			|Wikitext (//unicode//), usually from {{tt{wikklytext.base.load_wikitext()}}}|
		|encoding\
			|Desired output encoding (i.e. {{{'utf-8'}}})|
		|safe_mode\
			|True/False, whether to use Safe mode.|
		|setvars\
			|Variables to set into ~WikContext, as dict of:<br>{{{name: <str, unicode or int>}}}<br> \
				where 'name' can have a leading '$' to set sysvars.|
		|max_runtime\
			|Maximum time (in seconds) to run, or -1 for unlimited.|
		|url_resolver\
			|URL resolver. Must be a callable like [[default_URL_resolver()|#FUNC_default_URL_resolver]]. \
			If None, a default resolver will be used.|
		|tree_posthook\
			|Hook to call after ~ElementTree is complete, before generating XML. Will be called as: <br>\
				{{{tree_posthook(rootnode, context)}}} <br> Hook should modify tree in-place.|
		|plugin_dirs\
			|Paths to search for plugins. Can be a list of strings, a single string, or None.|
		|rendercache\
			|Instance of class in wikklytext.cache to perform caching.|
		|macro_handler\
			|Caller-defined macro handler. Will be called as:<br>\
			{{{
			handled, result = macro_handler(name, context, *elements)
			}}}\
			Returns:\
			* ''handled'': True/False if macro call was handled.
			* ''result'' is the macro return value, ready to be processed \
			by ''macro.process_macro_result''().|
		|kwargs\
			|//Undocumented// -- for backward compatibility with earlier keyword args. Do not \
			pass this directly.|
	
	|>|!Returns: {{{(xml, context)}}} |
		|xml\
			|Generated XML as an encoded bytestring|
		|context\
			|~WikContext that was used, in case user wants to inspect it.|
	"""
	from wikklytext.base import WikContext
	from wikklytext.eval import eval_wiki_elem
	
	setvars = setvars or {}
	
	if kwargs.has_key('plugin_dir'):
		# in 1.4.0 this was named 'plugin_dir' so accept if plugin_dirs not given
		plugin_dirs = plugin_dirs or kwargs.get('plugin_dir',None)
		deprecation("Change 'plugin_dir' to 'plugin_dirs' in args to WikklyText_to_XML()")
	
	wcontext = WikContext(restricted_mode=safe_mode,	
							max_runtime=max_runtime,
							url_resolver=url_resolver,
							plugin_dirs=plugin_dirs,
							rendercache=rendercache,
							macro_handler=macro_handler)
	
	# set any passed vars into the context
	for name, value in setvars.items():
		if isinstance(value, (str,unicode)):
			wcontext.var_set_text(name, value)
		elif isinstance(value, int):
			wcontext.var_set_int(name, value)
		else:
			raise WikError("Bad value in setvars")
		
	elem = WikklyText_to_Tree(wcontext, content)
	elem = eval_wiki_elem(wcontext, elem)
	
	# include errors from wcontext
	elist = elem.find('ErrorsList')
	for e in wcontext.parser.getErrors():
		elist.append(e)
		
	# call hook to postprocess tree before making XML
	if tree_posthook is not None:
		tree_posthook(elem, wcontext)
	
	xml = dumpxml(elem)
	return (xml, wcontext)
	
if __name__ == '__main__':
	import sys
	import wikklytext.base
	from wikklytext import loadxml
	
	if len(sys.argv) < 2:
		buf = wikklytext.base.load_wikitext('simple.txt')
	else:
		buf = wikklytext.base.load_wikitext(sys.argv[1])
		
	xml, context = WikklyText_to_XML(buf, 'utf-8', False)
	print xml
	
	# reparse as a sanity check
	#sio = StringIO(xml)
	#tree = ElementTree(None, sio)
	loadxml(xml)
	
