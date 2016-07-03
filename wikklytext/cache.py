"""
cache.py: Rendering cache.

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

"""
Caches accept and return Elements. The cache is free to optimize storage of Elements
any way it chooses.

Each cache will have a unique __init__() but the rest of the API is the same.
"""
from random import randint

class BaseCache(object):
	"""
	Base class for rendering caches. Do not instantiate directly.
	
	This class is also used to document the public interface, whereas the others
	have minimal documentation to avoid duplication.
	"""
	def __init__(self):
		# statistics
		self.nr_puts = 0
		self.nr_gets = 0
		self.nr_hits = 0
		
		# default expiration time (seconds)
		self.expiration_time = 100000000
		# default clean interval (counts)
		self.clean_interval = 1000
		
	def stats(self):
		return {'puts': self.nr_puts, 'gets': self.nr_gets, 'hits': self.nr_hits,
				'objects': self.nr_objects(), 'bytes': self.nr_bytes(),
				'expiration_time': self.expiration_time, 'clean_interval': self.clean_interval,
				'type': self.__class__.__name__}
		
	# public API
	def put_elem(self, key, elem):
		"""
		Store the given Element under the given key in the cache.
		
		|key|40-character string identifying the tree (usually the SHA-1 of the content used to generate it)|
		|tree|Element|
		"""
		self._put(key, elem)
		self.nr_puts += 1
	
	def get_elem(self, key):
		"""
		Try getting an Element from the cache.
		
		|key|40-character string identifying element (i.e. same key that would have been passed to put_element()|
		
		Returns Element if found or None if not.
		"""
		# see if its time to do a cache cleaning. note that this cache object
		# may be short-lived, so I do this statistically instead of keeping ad
		# counter that decrements until it reaches zero
		if randint(0, self.clean_interval) == 0:
			self.do_expire()
			
		elem = self._get(key)
		self.nr_gets += 1
		if elem is not None:
			self.nr_hits += 1
			
		return elem

	def clear_all(self):
		"""
		Clear the entire cache.
		"""
		raise NotImplementedError # subclass must implement

	def set_expire_time(self, seconds):
		"""
		Set amount of time entries remain in the cache before being 
		deleted. This affects new entries only; existing entries are
		not changed.
		"""
		self.expiration_time = seconds
		
	def set_clean_interval(self, count):
		"""
		Set interval for cleaning cache. Cache will be checked for
		expired entires once per count accesses (approximately).
		"""
		self.clean_interval = count
		
	def do_expire(self):
		"""
		Expire (remove) old entries in the cache.
		[Called periodically from get_elem()]
		"""
		pass # subclasses not required to implement
		
	def nr_objects(self):
		"""
		Get the number of objects stored in the cache.
		
		Can return -1 if not implemented for this cache type.
		"""
		raise NotImplementedError # subclass must implement

	def nr_bytes(self):
		"""
		Get the number of bytes stored in the cache.
		
		Can return -1 if not implemented for this cache type.
		"""
		raise NotImplementedError # subclass must implement

	# private API -- subclasses must implement
	def _put(self, key, elem):
		raise NotImplementedError
	
	def _get(self, key):
		raise NotImplementedError
		
class NullCache(BaseCache):
	"""
	A cache that does nothing. Used by default when no rendercache is given.
	"""
	def __init__(self):
		BaseCache.__init__(self)
		
	def clear_all(self):
		pass
	
	def nr_objects(self):
		return 0
	
	def nr_bytes(self):
		return 0
		
	def _put(self, key, elem):
		pass
	
	def _get(self, key):
		return None

class RamCache(BaseCache):
	"""
	A RAM-based cache.
	"""
	def __init__(self):
		BaseCache.__init__(self)
		self.cache = {}
		
	def clear_all(self):
		self.cache = {}
	
	def nr_objects(self):
		return len(self.cache)
	
	def nr_bytes(self):
		return -1 # don't know how many bytes are stored
		
	def _put(self, key, elem):
		self.cache[key] = elem
		
	def _get(self, key):
		return self.cache.get(key, None)
		
from wikklytext.base import ElementTree
import os
from stat import ST_SIZE
from time import time
from boodebr.util.locking import open_locked

# os.SEEK_END missing in Py2.3
SEEK_END = 2
	
class FileCacheSerialize(BaseCache):
	"""
	A file-based cache that serializes the Elements to XML.
	"""
	def __init__(self, rootdir):
		"|rootdir|Folder for cache storage. It should be empty, or at least used for no other purpose.|"
		BaseCache.__init__(self)
		self.rootdir = rootdir
		
	def clear_all(self):
		import shutil
		if os.path.isdir(self.rootdir):
			shutil.rmtree(self.rootdir)
	
	def nr_objects(self):
		return len(self._read_index())
	
	def nr_bytes(self):
		bytes = 0
		for size, exptime in self._read_index().values():
			bytes += size
			
		return bytes
		
	def _put(self, key, elem):
		#print "PUT ELEM",elem.tag
		name = self._filename(key)
		p,n = os.path.split(name)
		if not os.path.isdir(p):
			os.makedirs(p)
			
		f = open(name, 'wb')
		tree = ElementTree(element=elem)
		tree.write(f, 'utf-8')
		del f # be explicit
		
		index = open_locked(self._index())
		try:
			index.seek(0, SEEK_END)
			# don't worry if a line for 'key' already exists -- can be cleaned up later.
			# idea here is to just write the info as quickly as possible.
			index.write('%s %d %d\n' % (key, os.stat(name)[ST_SIZE], time()+self.expiration_time))
		finally:
			del index # explicitly del
		
	def _get(self, key):
		name = self._filename(key)
		if not os.path.isfile(name):
			return None
			
		f = open(name, 'rb')
		elem = ElementTree(file=f).getroot()
		del f # be explicit
		#print "GET ELEM",elem.tag,name
		return elem
		
	def _filename(self, key):
		# load/store as pathname "rootdir/key[:2]/key[2:]"
		sub = os.path.join(self.rootdir, key[:2])
		cf = os.path.join(sub, key[2:])
		return cf
		
	def _index(self):
		return os.path.join(self.rootdir, 'index')
		
	def _read_index(self):
		index = open_locked(self._index())
		try:
			objs = self._f_read_index(index)
		finally:
			del index # explicitly del
		
		return objs
	
	def _f_read_index(self, f):
		"Read index, given opened 'index' file."
		objs = {}
		for line in f:
			key, size, exptime = line.split()
			# later entries overwrite earlier entries
			objs[key] = (int(size), int(exptime))
					
		return objs
		
	def do_expire(self):
		#print "DO_EXPIRE"
		index = open_locked(self._index())
		try:
			objs = self._f_read_index(index)
			# reading the index has already removed duplicate entries, so all
			# I have to do is remove the expired items
			index.seek(0)
			index.truncate(0)
			
			for key,(size,exptime) in objs.items():
				if time() >= exptime:
					name = self._filename(key)
					#print "EXPIRE",key
					if os.path.isfile(name):
						os.unlink(name)
				else:
					# still valid, keep in index
					index.write('%s %d %d\n' % (key, size, exptime))
					
		finally:					
			del index
		
