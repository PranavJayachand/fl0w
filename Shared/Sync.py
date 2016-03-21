import os
import hashlib
import time
import base64
import random

import Routing
import sqlite3

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class File:
	def __init__(self, relpath, hash, mtime):
		self.relpath = relpath
		self.hash = hash
		self.mtime = mtime


	@property
	def db_repr(self):
		return [self.relpath, self.hash, self.mtime]


	def __eq__(self, other):
		if type(other) is File:
			return self.__dict__ == other.__dict__
		return False


	def __repr__(self):
		return "%s: %s, %d" % (self.relpath, self.hash, self.mtime)


class DeletedStorage:
	def __init__(self, db_path="deleted.db"):
		self.db = sqlite3.connect(db_path)
		self.cursor = self.db.cursor()
		self.files = []
		self.cursor.execute("create table if not exists files (file_id integer primary key autoincrement, relpath text, hash text, mtime integer)")
		for row in self.cursor.execute("select * from files"):
			self.files.append(File(row[1], row[2], row[3]))
		self.cursor.execute("delete from files")

	def add(self, file):
		if type(file) is File:
			if file not in self.files:
				self.files.append(file)
		else:
			raise TypeError("only objects of type File can be added")

	def remove(self, file):
		if type(file) is File:
			if file in self.files:
				del self.files[self.files.index(file)]
		else:
			raise TypeError("only objects of type File can be removed")

	def close(self):
		for file in self.files:
			self.cursor.execute("insert into files (relpath, hash, mtime) values (?, ?, ?)", file.db_repr)
		self.db.commit()
		self.db.close()


def relative_recursive_ls(path, relative_to, exclude=[]):
	if path[-1] != "/":
		path += "/"
	files = []
	for item in os.listdir(path):
		if item not in exclude:
			if os.path.isdir(path + item):
				files += relative_recursive_ls(path + item, relative_to, exclude)
			else:
				files.append(os.path.relpath(path + item, relative_to))
	return files


def md5(path):
	return hashlib.md5(open(path, "rb").read()).hexdigest()

def get_mtime(path):
	return os.path.getmtime(path)


def get_name_from_path(path):
	name = os.path.basename(path)
	if name:
		return name
	else:
		return None


def get_file_content(path):
	return open(path, "rb+").read()

def base64_str_decode(path):
	return base64.b64encode(get_file_content(path)).decode()

class ReloadHandler(FileSystemEventHandler):
	def __init__(self, sync):
		self.sync = sync

	def on_modified(self, event):
		if get_name_from_path(event.src_path) not in self.sync.exclude and not event.is_directory:
			self.sync.modified(event)


	def on_created(self, event):
		if get_name_from_path(event.src_path) not in self.sync.exclude and not event.is_directory:
			self.sync.created(event)


	def on_deleted(self, event):
		if get_name_from_path(event.src_path) not in self.sync.exclude and not event.is_directory:
			self.sync.deleted(event)


class SyncClient(Routing.ClientRoute):
	def __init__(self, sock, folder, route, exclude=[".DS_Store", ".git", ".fl0w"]):
		self.sock = sock
		self.folder = folder if folder[-1] == "/" else folder + "/"
		self.started = False
		self.route = route
		self.exclude = exclude
		self.files = relative_recursive_ls(folder, folder, exclude=self.exclude)
		self.suppressed_fs_events = []
		observer = Observer()
		observer.schedule(ReloadHandler(self), path=self.folder, recursive=True)
		observer.start()


	def start(self):
		out = {"list" : {}}
		for file in self.files:
			out["list"].update({file : {"mtime" : get_mtime(self.folder + file), 
				"md5" : md5(self.folder + file)}})
		self.sock.send(out, self.route)


	def suppress_fs_event(self, file):
		if not file in self.suppressed_fs_events:
			self.suppressed_fs_events.append(file)


	def unsuppress_fs_event(self, file):
		if file in self.suppressed_fs_events:
			del self.suppressed_fs_events[self.suppressed_fs_events.index(file)]


	def run(self, data, handler):
		if type(data) is dict:
			if "add" in data:
				for file in data["add"]:
					if not file in self.suppressed_fs_events:
						self.suppress_fs_event(file)
						folder_path = self.folder + os.path.dirname(file)
						if not os.path.exists(folder_path):
							os.makedirs(folder_path)
						if os.path.exists:
							open(self.folder + file, "wb+").write(base64.b64decode(data["add"][file]["content"]))
						else:
							open(self.folder + file, "ab+").write(base64.b64decode(data["add"][file]["content"]))
						os.utime(self.folder + file, (data["add"][file]["mtime"], data["add"][file]["mtime"]))
					else:
						self.unsuppress_fs_event(file)
			elif "del" in data:
				for file in data["del"]:
					self.suppress_fs_event(file)
					try:
						os.remove(self.folder + file)
					except FileNotFoundError:
						self.unsuppress_fs_event(file)
						Logging.warning("Possible server misbehaviour")
			elif "req" in data:
				for file in data["req"]:
					if file in self.files:
						self.sock.send({"add" : {file : {"content" : base64_str_decode(self.folder + file), 
							"mtime" : os.path.getmtime(self.folder + file)}}}, self.route)


	def modified(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath not in self.files:
			self.files.append(relpath)
		if not relpath in self.suppressed_fs_events:
			self.sock.send({"add" : {relpath : {"content" : base64_str_decode(event.src_path), 
				"mtime" : os.path.getmtime(event.src_path)}}}, self.route)
		else:
			self.unsuppress_fs_event(relpath)



	def created(self, event):
		self.modified(event)


	def deleted(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath in self.files:
			del self.files[self.files.index(relpath)]
		if not relpath in self.suppressed_fs_events: 
			self.sock.send({"del" : [relpath]}, self.route)
		else:
			self.unsuppress_fs_event(relpath)


class SyncServer(Routing.ServerRoute):
	REQUIRED = (Routing.BROADCAST, Routing.ROUTE)

	def __init__(self, folder, channel, exclude=[".DS_Store", ".git", ".keep", ".fl0w"], deleted_db_path="deleted.db", modified_hook=None, deleted_hook=None):
		self.folder = folder if folder[-1] == "/" else folder + "/"
		self.channel = channel
		self.exclude = exclude
		self.deleted_storage = DeletedStorage(deleted_db_path)
		self.modified_hook = modified_hook
		self.deleted_hook = deleted_hook
		self.broadcast_file_excludes = {}
		self.route = None # Set by REQUIRED
		self.broadcast = None # Set by REQUIRED


	def start(self, handler):
		self.files = relative_recursive_ls(self.folder, self.folder, exclude=self.exclude)
		observer = Observer()
		observer.schedule(ReloadHandler(self), path=self.folder, recursive=True)
		observer.start()


	def run(self, data, handler):
		if type(data) is dict:
			if "list" in data:
				client_files = []
				for file in data["list"]:
					client_file = File(file, data["list"][file]["md5"], data["list"][file]["mtime"])
					client_files.append(client_file)
					if not file in self.files:
						file = File(file, data["list"][file]["md5"], data["list"][file]["mtime"])
						if file in self.deleted_storage.files:
							handler.sock.send({"del" : [file.relpath]}, self.route)
						else:
							handler.sock.send({"req" : [file.relpath]}, self.route)
				for file in self.files:
					file = File(file, md5(self.folder + file), get_mtime(self.folder + file))
					if file not in client_files:
						handler.sock.send({"add" : {file.relpath : {"content" : base64_str_decode(self.folder + file.relpath), 
							"mtime" : os.path.getmtime(self.folder + file.relpath)}}}, self.route)
			elif "add" in data:
				for file in data["add"]:
					folder_path = self.folder + os.path.dirname(file)
					if not os.path.exists(folder_path):
						os.makedirs(folder_path)
					mode = "wb+" if os.path.exists(self.folder + file) else "ab+"
					self.broadcast_file_excludes[file] = handler
					open(self.folder + file, mode).write(base64.b64decode(data["add"][file]["content"]))
					os.utime(self.folder + file, (data["add"][file]["mtime"], data["add"][file]["mtime"]))
			elif "del" in data:
				for file in data["del"]:
					self.broadcast_file_excludes[file] = handler
					self.deleted_storage.add(File(file, md5(self.folder + file), get_mtime(self.folder + file)))
					try:
						os.remove(self.folder + file)
					except FileNotFoundError:
						del self.broadcast_file_excludes[file]
						Logging.warning("Possible client misbehaviour (%s:%d)" % (handler.info[0], handler.info[1]))


	def modified(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath not in self.files:
			self.files.append(relpath)
		exclude = []
		if relpath in self.broadcast_file_excludes:
			exclude.append(self.broadcast_file_excludes[relpath])
		self.broadcast.broadcast({"add" : {relpath : {
			"content" : base64_str_decode(event.src_path), 
			"mtime" : os.path.getmtime(event.src_path)}}}, self.route, self.channel, exclude=exclude)
		if exclude != []:
			del self.broadcast_file_excludes[relpath]


	def created(self, event):
		self.modified(event)


	def deleted(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath in self.files:
			del self.files[self.files.index(relpath)]
		exclude = []
		if relpath in self.broadcast_file_excludes:
			exclude.append(self.broadcast_file_excludes[relpath])
		self.broadcast.broadcast({"del" : [relpath]}, self.route, self.channel, exclude=exclude)
		if exclude != []:
			del self.broadcast_file_excludes[relpath]