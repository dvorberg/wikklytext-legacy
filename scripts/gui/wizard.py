"""
wikklytext.scripts.gui.wizard.py: wik 'control center' GUI - wizards.

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
import wx
import wx.wizard as wiz
from wx.richtext import RichTextCtrl
import boodebr.gui.wm as wm
import wikimages
import wx.lib.hyperlink as hlink
import wx.html as html
from wikklytext.scripts.gui.config import get_last_opendir, set_last_opendir
from wikklytext.wiki.core import WikklyWiki
import os, sys
from wikklytext.scripts.gui.config import CfgPathUser, CfgPathExe, startconfig

def show_progress(prg, msg, pctdone):
	prg.Update(pctdone, msg)

def run_wizard_first_run(parent):
	w = wiz.Wizard(parent, -1, "User Settings", wikimages.getWizLogoBitmap())
	
	page_usercfg = WikPageConfigLocation(w)
	
	w.GetPageAreaSizer().Add(page_usercfg)
	if not w.RunWizard(page_usercfg):
		return None # user cancelled
		
	r = page_usercfg.get()
	if r == 0:
		startconfig(CfgPathUser())
	elif r == 1:
		startconfig(CfgPathExe())
	elif r == 2:
		wm.info(parent, "Run program with the '--cfgpath' option to set the folder location.")
		sys.exit(0)
	else:
		raise Exception("Bad choice")

	return 0
	
def run_wizard_create_wiki(parent):
	w = wiz.Wizard(parent, -1, "Add Wiki", wikimages.getWizLogoBitmap())
	
	page_folder = WizPageFolder(w)
	page_format = WizPageFormat(w)
	
	page_html = WizPageHTMLName(w)
	page_sqlite = WizPageSQLiteName(w)
	page_server = WizPageServer(w)
	page_tuning = WizPageTuning(w)
	page_summary = WizPageSummary(w)
	
	page_folder.SetNext(page_format)
	
	page_format.SetPrev(page_folder)
	
	page_html.SetNext(page_server)
	page_sqlite.SetNext(page_server)
	
	page_server.SetNext(page_tuning)	
	page_tuning.SetPrev(page_server)
	
	page_tuning.SetNext(page_summary)
	page_summary.SetPrev(page_tuning)
	
	# rest of links are set dynamically
	page_format.SetPages(page_html, page_sqlite, page_server)
	page_summary.SetPages(page_folder, page_format, page_html, page_sqlite, page_server, page_tuning)
	
	w.GetPageAreaSizer().Add(page_folder)
	
	if not w.RunWizard(page_folder):
		return None # user cancelled
		
	from wikklytext.scripts.wik import do_create_wiki
	path = page_folder.getfolder()
	kind = page_format.getformat()
	if kind == 0:
		kind = 'text'
		filename = None
	elif kind == 1:
		kind = 'tiddlywiki'
		filename = page_html.getfilename()
	elif kind == 2:
		kind = 'sqlite'
		filename = page_sqlite.getfilename()
	else:
		raise Exception("Bad format")
		
	addr = page_server.getaddr()
	port = int(page_server.getport())
	prg = wx.ProgressDialog("Creating Wiki", ".....................................")

	do_create_wiki(path, kind, filename, addr, port, show_progress, prg)
	
	# set tuning parameters
	prg.Update(99, 'Tuning performance ...')
	
	wiki = WikklyWiki(path)
	
	storage = page_tuning.getstorage()
	if storage == 0: # local hard drive
		wiki.set_session_storage('file')
		wiki.set_session_timeout(60*60)
		wiki.set_cache_flag(True)
		wiki.set_metadb_flag(True)
	elif storage == 1: # network storage
		# file sessions are buggy over network storage
		wiki.set_session_storage('ram')
		wiki.set_session_timeout(60*60)
		wiki.set_cache_flag(True)
		wiki.set_metadb_flag(True)
	elif storage == 2: # USB
		# turn off all writing to conserve USB life
		wiki.set_session_storage('ram')
		wiki.set_session_timeout(60*60)
		wiki.set_cache_flag(False)
		wiki.set_metadb_flag(False)
		
	prg.Update(100,'')
	prg.Destroy() # else app will hang on exit
	
	wm.info(parent, "Wiki created OK!\n\nYou can now double-click on the wiki to run it and\nopen a browser window.")
	
	return path
	
class MyWizPage(wiz.PyWizardPage):
	def __init__(self, parent):
		wiz.PyWizardPage.__init__(self, parent)
		self.next = None
		self.prev = None
		
	def SetNext(self, page):
		self.next = page
		
	def SetPrev(self, page):
		self.prev = page
		
	def GetNext(self):
		return self.next
	
	def GetPrev(self):
		return self.prev

class WikPageConfigLocation(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Welcome to WikklyText!\n\nTo get started, I need to know where you'd like me to store your personal settings.""")
		vb.add(l,0)

		h = hlink.HyperLinkCtrl(self, label="More about these options", URL="http://wikklytext.com/wiki/WikGuiConfigFolder.html")
		vb.add(h,0)
		
		rb = wm.radiobox(self, "Choose a Configuration Path",
				["User folder (%s)" % CfgPathUser(),
				"Executable folder (%s)" % CfgPathExe(),
				"Other folder"], nr_cols=1)
		vb.add(rb, 0)
		
		self.rb = rb
		
		self.SetSizer(vb)

	def get(self):
		return int(self.rb)
		
class WizPageFolder(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Choose a location to store your wiki. I recommend\ncreating a new folder, or picking an empty folder here.""")
		vb.add(l,0)
	
		hb = wm.hbox()
		
		l = wm.label(self, 'Folder:')
		hb.add(l,0)
		
		s = wm.string(self, '')
		hb.add(s,5)
		self.s_rootdir = s
		
		b = wm.button(self, 'Browse ...', self.on_browse)
		hb.add(b,2)
	
		vb.add(hb,0)
		
		self.SetSizer(vb)

		self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.on_changing)
		
	def getfolder(self):
		return str(self.s_rootdir)
		
	def on_changing(self, ev):
		if ev.GetDirection() and not os.path.isdir(self.getfolder()):
			wm.error(self, "You must first choose or create a folder.")
			ev.Veto()
			
	def on_browse(self, ev):
		dlg = wx.DirDialog(self, "Select wiki root folder", defaultPath=get_last_opendir())
		if len(str(self.s_rootdir)):
			dlg.SetPath(str(self.s_rootdir))
			
		if dlg.ShowModal() != wx.ID_OK:
			return
			
		path = dlg.GetPath()
		set_last_opendir(path)
		self.s_rootdir.set(path)

class WizPageFormat(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Choose a storage format. Don't worry too much\nabout your choice here, you can always change it later.""")
		vb.add(l,0)
		
		h = hlink.HyperLinkCtrl(self, label="More about storage formats", URL="http://wikklytext.com/wiki/WhichFormat_.html")
		vb.add(h,0)
		
		rb = wm.radiobox(self, "Storage Format", 
				['Text files. Creates one .txt file per wiki item.', 
				'TiddlyWiki file. Entire wiki is stored in a single .html file.', 
				'SQLite Database. Wiki is stored in a single database file.'],
				nr_cols=1)
		vb.add(rb,0)
		rb.set(2)
		self.rb_format = rb
		
		self.SetSizer(vb)

	def getformat(self):
		return int(self.rb_format)

	def SetPages(self, page_html, page_sqlite, page_server):
		self.page_html = page_html
		self.page_sqlite = page_sqlite
		self.page_server = page_server
		
	def GetNext(self):
		fmt = self.getformat()
		if fmt == 0:
			# .txt - no filename to set
			self.page_server.SetPrev(self)
			return self.page_server
		elif fmt == 1:
			# .html - need filename
			self.page_html.SetPrev(self)
			self.page_server.SetPrev(self.page_html)
			return self.page_html
		elif fmt == 2:
			# sqlite - need filename
			self.page_sqlite.SetPrev(self)
			self.page_server.SetPrev(self.page_sqlite)
			return self.page_sqlite
		else:
			raise Exception("Unknown format")

class WizPageTuning(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """I will set some parameters to optimize performance for your\nintended usage. Please select the most appropriate choice below:""")
		vb.add(l,0)
		
		#h = hlink.HyperLinkCtrl(self, label="More about storage formats", URL="http://wikklytext.com/wiki/WhichFormat_.html")
		#vb.add(h,0)
		
		rb = wm.radiobox(self, "Storage Media", 
				['Local Hard Drive', 
				'Networked Hard Drive', 
				'USB Device'],
				nr_cols=1)
		vb.add(rb,0)
		rb.set(0)
		self.rb_storage = rb
		
		self.SetSizer(vb)

	def getstorage(self):
		return int(self.rb_storage)
		
class WizPageHTMLName(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Pick a name for your wiki HTML file.""")
		vb.add(l,0)
	
		hb = wm.hbox()
		
		l = wm.label(self, 'Filename:')
		hb.add(l,0)
		
		s = wm.string(self, 'wiki.html')
		hb.add(s,5)
		self.s_filename = s
		
		vb.add(hb,0)
		
		l = wm.label(self,"Your wiki will be stored in as a single TiddlyWiki HTML file.\nThis file will be stored in your wiki folder.")
		fn = l.GetFont()
		fn.SetStyle(wx.FONTSTYLE_SLANT)
		l.SetFont(fn)
		
		vb.add(l,0)
		
		self.SetSizer(vb)

	def getfilename(self):
		return str(self.s_filename)
		
class WizPageSQLiteName(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Pick a name for your wiki SQLite file.""")
		vb.add(l,0)
	
		hb = wm.hbox()
		
		l = wm.label(self, 'Filename:')
		hb.add(l,0)
		
		s = wm.string(self, 'wiki.db')
		hb.add(s,5)
		self.s_filename = s
		
		vb.add(hb,0)
		
		l = wm.label(self,"Your wiki will be stored in as a single SQLite database file.\nThis file will be stored in your wiki folder.")
		fn = l.GetFont()
		fn.SetStyle(wx.FONTSTYLE_SLANT)
		l.SetFont(fn)
		
		vb.add(l,0)
		
		self.SetSizer(vb)

	def getfilename(self):
		return str(self.s_filename)
	
class WizPageServer(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		l = wm.label(self, """Set the server parameters. Make sure to set a port number\nthat is not already in use.""")
		vb.add(l,0)
	
		hb = wm.hbox()
		
		l = wm.label(self, 'Address:')
		hb.add(l,0)
		
		s = wm.string(self, '127.0.0.1')
		hb.add(s,5)
		self.s_addr = s
		
		l = wm.label(self, 'Port:')
		hb.add(l,0)
		
		s = wm.string(self, '8000')
		hb.add(s,5)
		self.s_port = s
		
		vb.add(hb,0)
		
		self.SetSizer(vb)

	def getaddr(self):
		return str(self.s_addr)
		
	def getport(self):
		return str(self.s_port)
		
class WizPageSummary(MyWizPage):
	def __init__(self, parent):
		MyWizPage.__init__(self, parent)
		
		vb = wm.vbox()
		
		rt = RichTextCtrl(self, style=wx.VSCROLL|wx.HSCROLL)
		self.rt = rt
		
		rt.SetEditable(False)
		
		vb.add(rt,1)
		
		self.SetSizer(vb)

		self.Bind(wiz.EVT_WIZARD_PAGE_CHANGED, self.on_changed)
		
	def on_changed(self, ev):
		self.fill()
		
	def fill(self):
		rt = self.rt
		rt.Clear()
		rt.Enable(False)
		
		#rt.BeginFontSize(10)
		
		#tt = wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
			
		rt.BeginBold()
		rt.WriteText("Summary\n")
		rt.EndBold()
		
		rt.BeginLeftIndent(40)
		
		rt.WriteText("Folder: ")
		rt.BeginBold()
		rt.WriteText(self.page_folder.getfolder())
		rt.EndBold()
		rt.WriteText('\n')
		
		rt.WriteText("Format: ")
		fmt = self.page_format.getformat()
		if fmt == 0:
			rt.BeginBold()
			rt.WriteText('Text files')
			rt.EndBold()
		elif fmt == 1:
			rt.BeginBold()
			rt.WriteText('TiddlyWiki HTML file')
			rt.EndBold()
			rt.WriteText('\nFilename: ')
			rt.BeginBold()
			rt.WriteText(self.page_html.getfilename())
			rt.EndBold()
		elif fmt == 2:
			rt.BeginBold()
			rt.WriteText('SQLite database')
			rt.EndBold()
			rt.WriteText('\nFilename: ')
			rt.BeginBold()
			rt.WriteText(self.page_sqlite.getfilename())
			rt.EndBold()
			
		rt.WriteText('\nURL: ')
		rt.BeginBold()
		rt.WriteText("http://%s:%s\n" % (self.page_server.getaddr(), self.page_server.getport()))
		rt.EndBold()
		
		rt.WriteText('\nTuning: ')
		rt.WriteText('Tune for ')
		rt.BeginBold()
		rt.WriteText('%s ' % \
				['local', 'network', 'USB'][self.page_tuning.getstorage()])
		rt.EndBold()
		rt.WriteText('storage.')
		
		rt.WriteText("\n\nClick '")
		rt.BeginBold()
		rt.WriteText('Finish')
		rt.EndBold()
		rt.WriteText("' to create this wiki, or go back to change settings.")
		
		rt.EndLeftIndent()
		
	def SetPages(self, page_folder, page_format, page_html, page_sqlite, page_server, page_tuning):
		self.page_folder = page_folder
		self.page_format = page_format
		self.page_html = page_html
		self.page_sqlite = page_sqlite
		self.page_server = page_server
		self.page_tuning = page_tuning
	

