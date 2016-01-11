from sys import path
import os
import _thread

fl0w_path = os.path.dirname(os.path.realpath(__file__))
shared_path = os.path.dirname(os.path.realpath(__file__)) + "/Shared/"
if fl0w_path not in path:
	path.append(fl0w_path)
if shared_path not in path:
	path.append(shared_path)


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import sublime 
import sublime_plugin

import socket
from ESock import ESock
import VarSync
import Routing
from SublimeMenu import *

import webbrowser

def plugin_unloaded():
	observer.stop()
	try:
		fl0w.sock.close()
	except:
		pass
	print("Observer stopped!")


class HandledESock:
	def __init__(self, sock, disconnect):
		self._sock = sock
		self.disconnect = disconnect

	def __getattr__(self, attr):
		if attr == "send":
			return self.send
		return getattr(self._sock, attr)

	def send(self, data, prefix):
		try:
			self._sock.send(data, prefix)
		except OSError:
			self.disconnect()
			_thread.exit()

	def recv(self):
		try:
			return self._sock.recv()
		except OSError:
			self.disconnect()
			_thread.exit()


def sock_handler(sock, routes, handler):
	while 1:
		data = sock.recv()
		if data[1] in routes:
			routes[data[1]].run(data[0], handler)


class ReloadHandler(FileSystemEventHandler):
		def on_modified(self, event):
			print("Modified: %s" % event)

		def on_created(self, event):
			print("Created: %s" % event)

		def on_deleted(self, event):
			print("Deleted: %s" % event)

class Fl0w:
	def __init__(self):
		self.connected = False
		self.varsync = None
		self.window = None
		self.start_menu = Items()
		self.start_menu.add_item(Item("Connect", "Connect to a fl0w server", action=self.invoke_connect))
		self.start_menu.add_item(Item("About", "Information about fl0w", action=self.invoke_about))
		self.main_menu = Items()
		self.main_menu.add_item(Item("Choose Link", "Select Link on which code is executed", action=self.invoke_link_chooser))
		self.main_menu.add_item(Item("Info", "Server info", action=self.invoke_info))
		self.main_menu.add_item(Item("Disconnect", "Disconnect from server", action=self.invoke_disconnect))

		

	# Input invokers
	def invoke_connect(self):
		Input("Address:Port", initial_text="", on_done=self.connect).invoke(self.window)

	def invoke_about(self):
		if sublime.ok_cancel_dialog("fl0w by @robot0nfire", "robot0nfire.com"):	
			webbrowser.open("http://robot0nfire.com")

	def invoke_link_chooser(self):
		link_menu = Items()
		print(self.varsync.attrs)
		for link in self.varsync.links:
			print(link)

	def invoke_info(self):
		self.sock.send("", "info")

	class Info(Routing.ClientRoute):
		def run(self, data, fl0w):
			sublime.message_dialog(data)



	def invoke_disconnect(self):
		self.sock.close()
		self.connected = False
		sublime.message_dialog("Connection closed")



	def connect(self, connect_details):
		connect_details = connect_details.split(":")
		if len(connect_details) == 2:
			try:
				self.sock = HandledESock(ESock(socket.create_connection((connect_details[0], int(connect_details[1])))), self.invoke_disconnect)
				sublime.status_message("Connected to %s:%s." % (connect_details[0], connect_details[1]))
				self.connected = True
				self.varsync = VarSync.Client(self.sock)
				_thread.start_new_thread(sock_handler, (self.sock, {"info" : Fl0w.Info(), "varsync" : self.varsync}, self))
			except OSError as e:
				sublime.error_message("Error during connection creation:\n %s" % str(e))
		else:
			sublime.error_message("Invalid input.")



class Fl0wCommand(sublime_plugin.WindowCommand):
	def run(self, menu=None, action=None): 
		if fl0w.window == None:
			fl0w.window = self.window
		if not fl0w.connected:
			fl0w.start_menu.invoke(self.window)
		else:
			fl0w.main_menu.invoke(self.window)



fl0w = Fl0w()
observer = Observer()
observer.schedule(ReloadHandler(), path=".", recursive=True)
#observer.start()
