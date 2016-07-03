"""
wikklytext.eval.py: WikklyText evaluation. Part of the WikklyText suite.

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

from wikklytext.base import Element, ElementList, WikError
from copy import copy
	
def eval_wiki_macro_args(wcontext, elements):
	"""
	Evaluate all TextMacroArg nodes in elements, returning others untouched.

	Returns an Element with the evaluated elements as subnodes (you should
	not use the top Element, it is just a container. (An Element is returned
	because it acts both like a list and lets you do .find(), etc. as needed.)
	"""
	outnode = ElementList()
	for e in elements:
		if e.tag == 'TextMacroArg':
			for node in eval_wiki_text(wcontext, e.text):
				outnode.append(node)
		else:
			outnode.append(e)
	
	return outnode
	
def clonetop(node):
	"""
	Clone node but leave child nodes empty.
	"""
	e = Element(node.tag, copy(node.attrib))
	e.text = node.text
	e.tail = node.tail
	return e
	
def eval_wiki_elem(wcontext, elem):
	"""
	Take a parsed tree, produced by e.g. parse_wiki_text(), and evaluate
	all <MacroCall> nodes (including any nodes found recursively).
	
	Returns evaluated node (which may be elem or may be a new node).
	"""
	import wikklytext.macro

	# evaluate my subnodes first in case they are needed as macro args
	# (there could be interior <MacroCalls> that need to be evaluated first)
	subnodes = [eval_wiki_elem(wcontext, e) for e in elem]

	# is elem a <MacroCall>?
	if elem.tag == 'MacroCall':
		# subnodes are (name, *args) -- the result of the macro call replaces all nodes
		# (including <MacroCall>)
		try:
			return wikklytext.macro.call_macro(wcontext, subnodes[0].text, subnodes[1:])
		except WikError, exc:
			# pass error to parser and continue
			wcontext.parser.error(exc.message, exc.looking_at, exc.trace)
			return ElementList()

	elif elem.tag == 'PyCode':
		assert(len(elem) == 1 and elem[0].tag == 'TextPyCode')
		try:
			wikklytext.macro.insert_pycode(wcontext, elem[0].text)
		except WikError, exc:
			self.wcontext.parser.error(exc.message, exc.looking_at, exc.trace)

		return ElementList() # nothing to return
		
	else:
		# elem is a normal tag -- clone and set subnodes as children
		out = clonetop(elem)
		for e in subnodes:
			out.append(e)
			
		return out
		
def parse_wiki_text(wcontext, wikitext):
	"""
	Parse wikitext, returning the result. This is the lowest-level parser.
	All other renderers (XML, HTML) are built on top of this.
	
	|wcontext|The parent WikContext - any errors that occur will be added to this context's parser.|
	|wikitext|The wikitext to evaluate.|
	
	Returns an ElementList with the result elements as subnodes (the ElementList itself
	is meaningless - it is just a convenient container).
	
	Note that the returned list will be unevaluated -- it will contain <MacroCall> nodes.
	Call eval_wiki_elem() to finalize it.
	"""
	# try cache
	key = wcontext.make_digest(wikitext)
	elem = wcontext.rendercache.get_elem(key)
	if elem is not None:
		return elem
		
	from wikklytext.lexer import WikklyContentLexer
	
	l = WikklyContentLexer()
	
	# Create new parser instance for inner lexer.
	icontext = wcontext.copy()
	icontext.parser = wcontext.parser.makenew()
	icontext.parser.set_context(icontext)
	l.parse(wikitext, icontext)
	
	# propogate errors from inner parser to parent
	errlist = icontext.parser.getErrors()
	wcontext.parser.addParserErrors(errlist)
	
	# propogate variable changes back up
	wcontext.update(icontext)
	
	elem = icontext.parser.getInnerResult()
	wcontext.rendercache.put_elem(key, elem)
	return elem
	
def eval_wiki_text(wcontext, wikitext):
	"""
	Convenience routine to parse and evaluate wikitext at once.
	
	Returns resulting Element.
	"""
	elem = parse_wiki_text(wcontext, wikitext)
	return eval_wiki_elem(wcontext, elem)
	
