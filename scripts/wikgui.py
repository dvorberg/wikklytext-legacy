"""
wikklytext.scripts.wikgui.py: wik 'control center' GUI

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
import os, sys
from time import time
import wx
import wx.lib.mixins.listctrl as listmix
try:
	import wikklytext.scripts.gui.wikimages as wikimages
except ImportError:
	raise Exception("wikimages not found. Do you need to run gen_images.py?")
	
import boodebr.gui.wm as wm
import wx.lib.buttons as wxbuttons
from wikklytext.wiki.core import WikklyWiki
from wikklytext.scripts.gui.config import CFG, \
		startbestconfig, get_wiki_list, set_wiki_list, validconfig, set_last_opendir, \
		get_last_opendir, get_wik_cmd
from urllib import urlopen
import wikklytext.scripts.gui.wizard as wiz
		
class WikRunState(object):
	def __init__(self, path):
		self._path = path
		self._pid = None
		self._process = None
		self._errmsg = None
		self._logwin = None
		
	def __getitem__(self, i):
		"Make state into a list for use by the listctrl"
		wiki = WikklyWiki(self._path)
		if not wiki.initted():
			return '?'
			
		if i == 0:
			from wikklytext.wiki.core import SiteTitleText
			return SiteTitleText(wiki)
				
		elif i == 1:
			return self._path
			
		elif i == 2:
			url = 'http://%s:%s' % (wiki.get_server_addr(), wiki.get_server_port())
			return url
			
		elif i == 3:
			if self.error() is not None:
				return self.error()
			elif self.process() is None:
				return 'Stopped'
			else:
				return 'Running'
				
		else:
			return "BAD COLUMN"
			
	def title(self):
		return self[0]
		
	def path(self):
		return self[1]

	def setpath(self, path):
		self._path = path
		
	def url(self):
		return self[2]
		
	def status(self):
		return self[3]
		
	def setpid(self, pid):
		self._pid = pid
		
	def pid(self):
		return self._pid
		
	def setprocess(self, proc):
		self._process = proc
		
	def process(self):
		return self._process

	def error(self):
		return self._errmsg
		
	def seterror(self, msg):
		self._errmsg = msg

	def logwin(self):
		return self._logwin
		
	def setlogwin(self, win):
		self._logwin = win
		
class LoggingFrame(wx.Frame):
	def __init__(self, parent, title):
		wx.Frame.__init__(self,parent,-1,title)
		
		vb = wm.vbox()
		
		t = wm.text(self, '')
		vb.add(t,1,border=0)
		self.text = t
		t.set_editable(False)
		
		self.Bind(wx.EVT_CLOSE, self.on_close)
		
		self.SetSizer(vb)
		vb.SetSizeHints(self)
		self.SetAutoLayout(True)
		self.SetSize((400,300))

	def on_close(self, ev):
		#print "VETO"
		ev.Veto(True)
		# hide instead of closing
		self.Show(False)
		
	def addtext(self, text):
		self.text.AppendText(text)
		
class DlgWikiConfig(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, -1, "Wiki Configuration")
		
		vb = wm.vbox()
		
		hb = wm.hbox()
		
		l = wm.label(self, 'Location:')
		hb.add(l,0)
		
		s = wm.string(self, '')
		hb.add(s, 5)
		self.s_rootdir = s
		
		b = wm.button(self, 'Browse ...', self.on_choose_rootdir)
		hb.add(b, 2)
		self.b_browse_rootdir = b
		
		vb.add(hb,1)
		
		hb = wm.hbox()
		
		l = wm.label(self, 'Storage format:')
		hb.add(l,0)
		self.l_format = l
		
		cb = wm.combo(self, ['Text (.txt) files', 'TiddlyWiki (.html) file', 'SQLite database'],
					self.on_choose_format)
		hb.add(cb,1)
		self.cb_format = cb
		
		vb.add(hb,1)
		
		hb = wm.hbox()
		
		l = wm.label(self, 'Filename:')
		hb.add(l,0)
		self.l_filename = l
		
		s = wm.string(self, '')
		hb.add(s, 5)
		self.s_filename = s
		
		b = wm.button(self, 'Browse ...')
		hb.add(b, 2)
		self.b_browse_file = b
		
		vb.add(hb,1)

		hb = wm.hbox()

		l = wm.label(self, 'Server address:')
		hb.add(l,0)
		self.l_server_addr = l
		
		s = wm.string(self, '127.0.0.1')
		hb.add(s, 5)
		self.s_server_addr = s
		
		l = wm.label(self, 'Port:')
		hb.add(l,0)
		self.l_server_port = l
		
		s = wm.string(self, '8000')
		hb.add(s, 5)
		self.s_server_port = s
		
		vb.add(hb,1)

		hb = wm.hbox()
		
		b = wm.button(self,'Save',self.on_save)
		hb.add(b,1)
		
		b = wm.button(self, 'Cancel',self.on_cancel)
		hb.add(b,1)
		
		b = wm.button(self, 'Help')
		hb.add(b,1)
		
		vb.add(hb,1)
		
		self.SetSizer(vb)
		vb.SetSizeHints(self)
		self.SetAutoLayout(True)
		
		wx.CallAfter(self.update_enables)
		
	def on_save(self,ev):
		self.EndModal(wx.ID_OK)
	
	def on_cancel(self,ev):
		self.EndModal(wx.ID_CANCEL)
		
	def setpath(self, path):
		"Set from an existing wiki at the given rootdir"
		wiki = WikklyWiki(path)
		if not wiki.initted():
			self.s_rootdir.set('')
			self.cb_format.set(-1)
			self.s_filename.set('')
			self.s_server_addr.set('')
			self.s_server_port.set('')
		else:
			self.s_rootdir.set(path)
			
			kinds = {'text': 0, 'tiddlywiki': 1, 'sqlite': 2}
			self.cb_format.set(kinds[wiki.get_kind()])
			
			if wiki.get_kind() in ['tiddlywiki','sqlite']:
				self.s_filename.set(wiki.get_filename())
			else:
				self.s_filename.set('')
				
			self.s_server_addr.set(wiki.get_server_addr())
			self.s_server_port.set(str(wiki.get_server_port()))
			
		self.update_enables()
		
	def update_enables(self):
		path = str(self.s_rootdir)
		w = WikklyWiki(path)
		if not len(path) or not os.path.isdir(path):
			self.l_format.Enable(False)
			self.cb_format.Enable(False)
			self.l_filename.Enable(False)
			self.s_filename.Enable(False)
			self.b_browse_file.Enable(False)
			self.l_server_addr.Enable(False)
			self.s_server_addr.Enable(False)
			self.l_server_port.Enable(False)
			self.s_server_port.Enable(False)
		elif w.initted():
			self.l_format.Enable(False)
			self.cb_format.Enable(False)
			self.l_filename.Enable(False)
			self.s_filename.Enable(False)
			self.b_browse_file.Enable(False)
		else:
			self.l_format.Enable(True)
			self.cb_format.Enable(True)
			if int(self.cb_format) in [1,2]:
				self.l_filename.Enable(True)
				self.s_filename.Enable(True)
				self.b_browse_file.Enable(True)
			else:
				self.l_filename.Enable(False)
				self.s_filename.Enable(False)
				self.b_browse_file.Enable(False)
				
			self.l_server_addr.Enable(True)
			self.s_server_addr.Enable(True)
			self.l_server_port.Enable(True)
			self.s_server_port.Enable(True)
					
	def on_choose_format(self, ev):
		self.update_enables()
		
	def on_choose_rootdir(self, ev):
		dlg = wx.DirDialog(self, "Select wiki root folder")
		if len(str(self.s_rootdir)):
			dlg.SetPath(str(self.s_rootdir))
			
		if dlg.ShowModal() != wx.ID_OK:
			return
			
		path = dlg.GetPath()
		self.s_rootdir.set(path)
		
		w = WikklyWiki(path)
		if w.initted():
			kind = w.get_kind()
			if kind == 'text':
				self.cb_format.set(0)
			elif kind == 'tiddlywiki':
				self.cb_format.set(1)
				self.s_filename.set(w.get_filename())
			elif kind == 'sqlite':
				self.cb_format.set(2)
				self.s_filename.set(w.get_filename())
			else:
				raise Exception("Unknown format")
					
			self.s_server_addr.set(w.get_server_addr())
			self.s_server_port.set(str(w.get_server_port()))
		else:
			self.cb_format.set(-1)
			self.s_server_addr.set('127.0.0.1')
			self.s_server_port.set('8000')
			
		self.update_enables()
		
	def get_rootdir(self):
		return str(self.s_rootdir)
		
	def get_server_addr(self):
		return str(self.s_server_addr)
	
	def get_server_port(self):
		return int(str(self.s_server_port))
		
class WikListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
	def __init__(self, parent, ID, pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)

class WikListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		tID = wx.NewId()
		
		vbox = wm.vbox()
		
		self.images = wx.ImageList(15,16)
		
		self.img_uparrow = self.images.Add(wikimages.getUpArrowBitmap())
		self.img_downarrow = self.images.Add(wikimages.getDownArrowBitmap())
		self.img_greenball = self.images.Add(wikimages.getGreenBallBitmap())
		self.img_hollowcircle = self.images.Add(wikimages.getHollowCircleBitmap())
		self.img_error = self.images.Add(wikimages.getErrorBitmap())
		
		self.list = WikListCtrl(self, tID,
								 style=wx.LC_REPORT 
								 #| wx.BORDER_SUNKEN
								 | wx.BORDER_NONE
								 | wx.LC_EDIT_LABELS
								 | wx.LC_SORT_ASCENDING
								 #| wx.LC_NO_HEADER
								 #| wx.LC_VRULES
								 #| wx.LC_HRULES
								 #| wx.LC_SINGLE_SEL
								 )
		
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_doubleclick, self.list)
		
		self.list.SetImageList(self.images, wx.IMAGE_LIST_SMALL)
		vbox.Add(self.list, 1, wx.EXPAND)
		
		self.init_columns()

		# Now that the list exists we can init the other base class,
		# see wx/lib/mixins/listctrl.py
		self.itemDataMap = {}
		listmix.ColumnSorterMixin.__init__(self, 4)
		#self.SortListItems(0, True)

		for path in get_wiki_list():
			self.add_wiki(path)
		
		# make running PIDs to wiki paths
		self.procmap = {}
		
		# catch processes when they exit
		self.Bind(wx.EVT_END_PROCESS, self.on_process_ended)
		
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
		self.timer.Start(1000, oneShot=True)
		
		self.SetSizer(vbox)
		vbox.SetSizeHints(self)
		self.SetAutoLayout(True)

	def on_timer(self, ev):
		for state in self.get_all():
			if state.process() is None:
				continue
				
			stream = state.process().GetInputStream()

			if stream.CanRead():
				text = stream.read()
				#print "MORE (STDOUT) TEXT",text
				state.logwin().addtext(text)

			stream = state.process().GetErrorStream()

			if stream.CanRead():
				text = stream.read()
				#print "MORE (ERROR) TEXT",text
				state.logwin().addtext(text)

		self.timer.Start(1000, oneShot=True)
		
	def on_doubleclick(self, ev):
		id_state = self.list.GetItemData(ev.GetIndex())
		state = self.itemDataMap[id_state]
		self.do_browse(state)
		
	def stop_wiki(self, state):
		"Stop wiki, if it is running"
		if state.process() is not None:
			#print "DETACH",state.process()
			state.process().Detach()
			state.process().CloseOutput()
			#print "KILL PROCESS",state.pid()
			wx.Kill(state.pid(), wx.SIGKILL)
			state.setprocess(None)
			state.setpid(None)
			self.update_row(state)
			
	def on_exit(self):
		#print "EXITING"
		for state in self.get_all():
			self.stop_wiki(state)
				
	def get_all(self):
		"Get WikiRunState for all wikis"
		states = []
		for row in range(self.list.GetItemCount()):
			id_state = self.list.GetItemData(row)
			states.append(self.itemDataMap[id_state])

		return states

	def get_selected(self):
		"Get WikiRunState for all selected rows"
		sel = []
		for row in range(self.list.GetItemCount()):
			if self.list.GetItemState(row, wx.LIST_STATE_SELECTED):
				id_state = self.list.GetItemData(row)
				sel.append(self.itemDataMap[id_state])

		return sel

	def on_stop(self):
		for state in self.get_selected():
			self.stop_wiki(state)

	def check_wiki_running(self, state):
		try:
			u = urlopen(state.url())
			return True
		except:
			return False

	def do_browse(self, state):			
		# start wiki if not already running
		if state.process() is None:
			if self.check_wiki_running(state):
				wm.error(self, 'Wiki "%s" appears to be running already.\n\nStop wiki and try again.' % state.path())
				return
				
			self.run_wiki(state)
			
			# wait for wiki to start
			wx.BeginBusyCursor()
			t0 = time()
			ok = 0
			while (time() - t0) < 15:
				if self.check_wiki_running(state):
					ok = 1
					break
			
			wx.EndBusyCursor()
			
			if not ok:
				state.seterror('Wiki not responding')
				self.update_row(state)
				
		wx.LaunchDefaultBrowser(state.url())
		
	def on_browse(self):
		for state in self.get_selected():
			self.do_browse(state)
	
	def on_viewlog(self):
		for state in self.get_selected():
			state.logwin().Show(True)
	
	def on_remove(self):
		states = self.get_selected()
		if not len(states):
			return
			
		if wm.yesno(self, "Remove selected wikis from the list?") != wx.ID_YES:
			return
			
		for state in states:
			# make sure its not running
			self.stop_wiki(state)
			# remove from listctrl and configfile
			row = self.list.FindItemData(-1, id(state))
			paths = get_wiki_list()
			i = paths.index(state.path())
			del paths[i]
			set_wiki_list(paths)
			self.list.DeleteItem(row)
			
	def on_restart(self):
		for state in self.get_selected():
			self.stop_wiki(state)	
			self.update_row(state)
			self.run_wiki(state)
			
	def run_wiki(self, state):
		if state.process() is not None:
			wm.error(self, 'Wiki is already running')
			return
			
		wikexe, exepath = get_wik_cmd()
		if wikexe is None:
			wm.error(self,"I cannot determine how to run wik. Please report this to\nthe mailing list (http://groups.google.com/group/wikklytext)\nso that a fix can be developed.")
			return
			
		proc = wx.Process(self) # send events to me
		proc.Redirect() # redirect stdin/stdout to pipes
		
		cmd = '%s -d %s --no-respawn serve' % (wikexe, state.path())
		pid = wx.Execute(cmd, wx.EXEC_ASYNC, proc)
		#print "STARTED",pid
		state.setpid(pid)
		state.setprocess(proc)
		state.seterror(None) # will set later if fails
		self.update_row(state)
		
	def on_process_ended(self, ev):
		#print "ENDED pid=%s, exitcode=%s" % (ev.GetPid(), ev.GetExitCode())
		for state in self.get_all():
			if state.pid() == ev.GetPid():
				state.setprocess(None)
				state.setpid(None)
				self.update_row(state)
				
	def on_configure(self):
		for state in self.get_selected():
			dlg = DlgWikiConfig(self)
			dlg.setpath(state.path())
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.get_rootdir()
				addr = dlg.get_server_addr()
				port = dlg.get_server_port()
				
				wiki = WikklyWiki(path)
				wiki.set_server_addr(addr)
				wiki.set_server_port(port)
		
				state.setpath(path)
				
				self.update_row(state)
				
	def add_row(self):
		# title
		item = wx.ListItem()
		item.SetMask(wx.LIST_MASK_TEXT | wx.LIST_MASK_FORMAT | wx.LIST_MASK_IMAGE)
		item.SetAlign(wx.LIST_FORMAT_LEFT)
		item.SetText('')
		item.SetImage(-1)
		item.SetColumn(0)
		
		row = self.list.InsertItem(item)
		
		# set Location
		item = wx.ListItem()
		item.SetMask(wx.LIST_MASK_TEXT | wx.LIST_MASK_FORMAT)
		item.SetAlign(wx.LIST_FORMAT_LEFT)
		item.SetText('')
		item.SetId(row)
		item.SetColumn(1)
		
		self.list.SetItem(item)
		
		# set URL
		item = wx.ListItem()
		item.SetMask(wx.LIST_MASK_TEXT | wx.LIST_MASK_FORMAT)
		item.SetAlign(wx.LIST_FORMAT_CENTER)
		item.SetText('')
		item.SetId(row)
		item.SetColumn(2)
		
		self.list.SetItem(item)
		
		# set Status
		item = wx.ListItem()
		item.SetMask(wx.LIST_MASK_TEXT | wx.LIST_MASK_FORMAT | wx.LIST_MASK_IMAGE)
		item.SetAlign(wx.LIST_FORMAT_CENTER)
		item.SetImage(-1)
		item.SetText('')
		item.SetId(row)
		item.SetColumn(3)
		
		self.list.SetItem(item)
		
		return row
		
	def update_row(self, state):
		"Update the list row that is associated with 'state'"
		
		row = self.list.FindItemData(-1,id(state))
		
		item = self.list.GetItem(row, 0)
		item.SetText(state.title())
		
		if state.process() is not None:
			item.SetImage(self.img_greenball)
		else:
			item.SetImage(self.img_hollowcircle)
			
		self.list.SetItem(item)
		
		item = self.list.GetItem(row, 1)
		item.SetText(state.path())
		self.list.SetItem(item)
		
		item = self.list.GetItem(row, 2)
		item.SetText(state.url())
		self.list.SetItem(item)

		item = self.list.GetItem(row, 3)
		
		if state.error() is not None:
			item.SetImage(self.img_error)
		else:			
			item.SetImage(-1)
			
		item.SetText(state.status())
		
		self.list.SetItem(item)

		self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(1, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(2, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(3, 100)

		wx.CallAfter(self.sanity_check_list)
		
		#wx.SafeYield()
		
	def add_wiki(self, path):
		wiki = WikklyWiki(path)
		
		state = WikRunState(path)
		win = LoggingFrame(self, 'Log of %s' % path)
		win.Show(False)
		state.setlogwin(win)
		self.itemDataMap[id(state)] = state
		
		row = self.add_row()
		
		self.list.SetItemData(row, id(state))
		
		self.update_row(state)
		
	def init_columns(self):
		self.list.InsertColumn(0, "SiteTitle")
		self.list.InsertColumn(1, "Location")
		self.list.InsertColumn(2, "URL", wx.LIST_FORMAT_CENTER)
		self.list.InsertColumn(3, "Status")
		
		self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(1, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(2, wx.LIST_AUTOSIZE)
		self.list.SetColumnWidth(3, 100)
			
	def sanity_check_list(self):
		pathmap = set()
		urlmap = set()
		
		for path in get_wiki_list():
			if path in pathmap:
				wm.error(self, 'Duplicate path in list:\n\n%s' % path)
				
			pathmap.add(path)
			
			wiki = WikklyWiki(path)
			url = '%s:%s' % (wiki.get_server_addr(), wiki.get_server_port())
			if url in urlmap:
				wm.error(self, 'Duplicate server address/port:\n\n%s' % url)
				
			urlmap.add(url)
			
	# Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
	def GetListCtrl(self):
		return self.list

	# Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
	def GetSortImages(self):
		return (self.img_downarrow, self.img_uparrow)

class WikMainFrame(wx.Frame):
	def __init__(self,parent):
		wx.Frame.__init__(self,parent,-1,'Wik Control Center')

		vbox = wm.vbox()
		p = WikListCtrlPanel(self)
		vbox.add(p,6,border=0)
		self.panel = p
		
		hb = wm.hbox()
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getAddBitmap(),
				label = 'Add ...')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_add, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getBrowseBitmap(),
				label = 'Browse')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_browse, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getReloadBitmap(),
				label = 'Restart')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_restart, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getRedXBitmap(),
				label = 'Stop')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_stop, b)
		
		vbox.add(hb,1,border=0)
		
		hb = wm.hbox()
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getWrenchBitmap(),
				label = 'Configure ...')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_configure, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getInspectBitmap(),
				label = 'View Log')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_viewlog, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getTrashBitmap(),
				label = 'Remove')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_remove, b)
		
		b = wxbuttons.GenBitmapTextButton(self, 
				bitmap = wikimages.getHelpBitmap(),
				label = 'Help')
		hb.add(b,1,border=0)
		self.Bind(wx.EVT_BUTTON, self.on_help, b)
		
		vbox.add(hb, 1, border=0)
		
		self.Bind(wx.EVT_CLOSE, self.on_close)
		
		self.SetIcon(wikimages.getMainIconIcon())
		
		self.SetSizer(vbox)
		vbox.SetSizeHints(self)
		self.SetAutoLayout(True)
		
		wx.CallAfter(self.on_startup)
		
	def on_help(self, ev):
		wx.LaunchDefaultBrowser('http://wikklytext.com')
		
	def on_viewlog(self, ev):
		self.panel.on_viewlog()
	
	def on_browse(self, ev):
		self.panel.on_browse()
		
	def on_close(self, ev):
		self.panel.on_exit()
		ev.Skip()
		
	def on_configure(self, ev):
		self.panel.on_configure()
		
	def on_restart(self, ev):
		self.panel.on_restart()
	
	def on_stop(self, ev):
		self.panel.on_stop()
		
	def on_startup(self):
		if validconfig():
			return
		
		if wiz.run_wizard_first_run(self) is None:
			wm.error(self, 'Must set a configuration path before continuing.')
			sys.exit(0)
					
		# make sure cfgfile exists so I can find it on the next run
		set_wiki_list([])
		
	def on_remove(self, ev):
		self.panel.on_remove()
		
	def run_wizard_create_wiki(self):
		path = wiz.run_wizard_create_wiki(self)
		if path is None:
			return # user cancelled
			
		paths = get_wiki_list()
		paths.append(path)
		set_wiki_list(paths)
		self.panel.add_wiki(path)
		
	def add_existing_wiki(self):
		dlg = wx.DirDialog(self, defaultPath = get_last_opendir(),
				style=wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST)
		if dlg.ShowModal() != wx.ID_OK:
			return
			
		wikiroot = dlg.GetPath()
		set_last_opendir(wikiroot)
		
		wiki = WikklyWiki(wikiroot)
		if not wiki.initted():
			wm.error(self, 'No wiki found in "%s"' % wikiroot)
			return
		
		paths = get_wiki_list()
		paths.append(wikiroot)
		set_wiki_list(paths)
		self.panel.add_wiki(wikiroot)
		
	def on_add(self, ev):
		r = wm.ask_choice(self, '',
				['Create new wiki', 'Add an existing wiki to list'],
				'Create wiki or use existing?')
		
		if r == 0:
			self.run_wizard_create_wiki()
		elif r == 1:
			self.add_existing_wiki()
		
def rungui(configpath):
	startbestconfig(configpath)
	
	# create main window 
	app = wx.PySimpleApp()

	frame = WikMainFrame( None )
	frame.Show(True)
	
	app.SetTopWindow(frame)

	wm.enable_exc_handler()
	
	app.MainLoop()

# for running as a standalone script -- I have to be invoked
# from wik, so just add a stub loader. I also expect (above) to
# be able to do "wikgui cmd ..." and get the same results as
# from running "wik cmd ..."
def main():
	import wikklytext.scripts.wik as wik
	wik.main()

if __name__ == '__main__':
	main()


		
