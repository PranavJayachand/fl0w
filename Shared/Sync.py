import os
import hashlib
import time
import base64

import Routing

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


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
	def __init__(self, sock, folder, route, exclude=[".DS_Store", ".git"]):
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
			out["list"].update({file : {"mtime" : os.path.getmtime(self.folder + file), 
				"md5" : md5(self.folder + file)}})
		self.sock.send(out, self.route)
		self.started = True

	def stop(self):
		self.started = False


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
					if not file in self.suppressed_fs_events:
						os.remove(self.folder + file)
					else:
						self.unsuppress_fs_event(file)
			elif "req" in data:
				for file in data["req"]:
					if file in self.files:
						self.sock.send({"add" : {file : {"content" : base64_str_decode(self.folder + file), 
							"mtime" : os.path.getmtime(self.folder + file)}}}, self.route)


	def modified(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath not in self.files:
			self.files.append(relpath)
		self.sock.send({"add" : {relpath : {"content" : base64_str_decode(event.src_path), 
				"mtime" : os.path.getmtime(event.src_path)}}}, self.route)
		self.suppress_fs_event(relpath)



	def created(self, event):
		self.modified(event)


	def deleted(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath in self.files:
			del self.files[self.files.index(relpath)]
		self.sock.send({"del" : [relpath]}, self.route)
		self.suppress_fs_event(relpath)
		

class SyncServer(Routing.ServerRoute):
	REQUIRED = (Routing.BROADCAST, Routing.ROUTE)

	def __init__(self, folder, channel, exclude=[".DS_Store", ".git"]):
		self.folder = folder if folder[-1] == "/" else folder + "/"
		self.channel = channel
		self.exclude = exclude
		self.suppressed_fs_events = []
		self.route = None # Set by REQUIRED
		self.broadcast = None # Set by REQUIRED


	def start(self):
		self.files = relative_recursive_ls(self.folder, self.folder, exclude=self.exclude)
		observer = Observer()
		observer.schedule(ReloadHandler(self), path=self.folder, recursive=True)
		observer.start()


	def suppress_fs_event(self, file):
		if not file in self.suppressed_fs_events:
			self.suppressed_fs_events.append(file)


	def unsuppress_fs_event(self, file):
		if file in self.suppressed_fs_events:
			del self.suppressed_fs_events[self.suppressed_fs_events.index(file)]


	def run(self, data, handler):
		if type(data) is dict:
			if "list" in data:
				for file in data["list"]:
					if data["list"][file]["mtime"] < handler.last_stop:
						if file in self.files:
							if data["list"][file]["mtime"] < os.path.getmtime(self.folder + file):
								handler.sock.send({"add" : {relpath : {
									"content" : base64_str_decode(event.src_path), 
									"mtime" : os.path.getmtime(event.src_path)}}}, self.route)
							elif data["list"][file]["mtime"] > os.path.getmtime(self.folder + file):
								handler.sock.send({"req" : [file]}, self.route)
						else:
							handler.sock.send({"del" : [file]}, self.route)
					else:
						if file not in self.files:
							handler.sock.send({"req" : [file]}, self.route)
			elif "add" in data:
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
					os.remove(self.folder + file)


	def modified(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath not in self.files:
			self.files.append(relpath)
		self.broadcast.broadcast({"add" : {relpath : {
			"content" : base64_str_decode(event.src_path), 
			"mtime" : os.path.getmtime(event.src_path)}}}, self.route, self.channel)
		suppress_fs_event(relpath)


	def created(self, event):
		self.modified(event)


	def deleted(self, event):
		relpath = os.path.relpath(event.src_path, self.folder)
		if relpath in self.files:
			del self.files[self.files.index(relpath)]
		self.broadcast.broadcast({"del" : [relpath]}, self.route, self.channel)
		self.suppress_fs_event(relpath)