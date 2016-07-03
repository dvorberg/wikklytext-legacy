"""
wikklytext.scripts.gui.config.py: wik 'control center' GUI - configuration.

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
from boodebr.config import *
import os, sys
from wikklytext.wiki.core import WikklyWiki

# configfile, set below
global CFG
CFG = None

def validconfig():
	return (CFG is not None and CFG.file_exists())
		
def startconfig(path):
	global CFG
	CFG = configfile(os.path.join(path, 'wikgui.json'))
	
def startbestconfig(configpath):
	global CFG
	
	nameUser = os.path.join(CfgPathUser(), 'wikgui.json')
	nameExe = os.path.join(CfgPathExe(), 'wikgui.json')
	
	# decide where to get configuration
	if configpath is not None:
		# --cfgpath overrides all
		CFG = configfile(os.path.join(configpath, 'wikgui.json'))
		# ensure file exists so won't prompt user when not found
		# in auto location
		set_wiki_list(get_wiki_list())
		#print "USING CONFIGFILE IN",configpath
	elif os.path.isfile(nameUser):
		# user-data path is next priority
		CFG = configfile(nameUser)
		#print "USING CONFIGFILE",nameUser
	elif os.path.isfile(nameExe):
		# executable path is next priority
		CFG = configfile(nameExe)
		#print "USING CONFIGFILE",nameExe
	else:
		CFG = None # want an error if I forget to set it
		#print "NO CONFIGFILE"
		
# potential locations for config file
def CfgPathUser():
	"Standard user folder"
	return user_data_path('WikklyText')
	
def CfgPathExe():
	"Location of wik executable"
	exe,path = get_wik_cmd()
	return path
	
# config setters/getters

def set_wiki_list(paths):
	if CFG is not None:
		CFG.set_list('/Preferences', 'wiki_paths', paths)
	
def get_wiki_list():
	if CFG is None:
		return []
		
	# remove any duplicates that may have snuck in due to deleting
	# and re-adding a wiki on the same path. Will eventually be
	# removed next time user saves config.
	#
	# ** do NOT remove any paths that don't exist - might be temporarily
	# ** unavailble due to network outage, etc.
	paths = set() 
	for path in CFG.get_list('/Preferences', 'wiki_paths', []):
		if WikklyWiki(path).initted():
			paths.add(path)
			
	return list(paths)

def set_last_opendir(path):
	if CFG is not None:
		CFG.set_str('/Preferences', 'last_opendir', path)
		
def get_last_opendir():
	if CFG is None:
		return os.getcwd()
		
	return CFG.get_str('/Preferences', 'last_opendir', os.getcwd())
	
def get_wik_cmd():
	"""
	Get command for running 'wik'
	Returns:
		(cmd, path)
		
	Where:
		cmd = Full command line to run 'wik' (or 'wikgui')
		path = Path to executable (for information).
	"""
	# decide if I was run as:
	#	python wik-scriptname
	# or:
	#   wik-as-exe
	#
	# known cases:
	# Win32 - "python wik.py"
	#   exe = PATH1\python.exe, argv=['PATH2\wik.py']
	# Win32 - running wik as installed
	#   exe = PATH1\python.exe, argv=['PATH2\wik-script.py']
	# Win32 - running wik.exe
	#   exe = PATH1\wik.exe, argv=['PATH1\wik.exe']
	# Ubuntu - running wik as installed
	#   exe = PATH1\python, argv=['PATH2\wik']
	path,name = os.path.split(sys.executable)
	if name.lower() in ['python', 'python.exe', 'pythonw', 'pythonw.exe']:
		# I was run as "python SCRIPTNAME"
		for arg in sys.argv:
			if os.path.isfile(arg):
				path,name = os.path.split(arg)
				#print "EXEPATH",path
				if name.lower() in ['wik.py', 'wik-script.py', 'wik',
								'wikgui.py', 'wikgui-script.py', 'wikgui']:
					return ('%s %s' % (sys.executable, arg), path)
					
		return None # unknown
		
	elif name.lower() in ['wik', 'wik.exe', 'wikgui', 'wikgui.exe']:
		# I was run as "wik" (or "wikgui")
		#print "EXEPATH",path
		return (sys.executable, path)
		
	else:
		return (None, None) # unknown
		

