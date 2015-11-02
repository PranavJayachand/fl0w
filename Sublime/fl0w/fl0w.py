from sys import path
import os
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
from SublimeMenu import *

def plugin_unloaded():
	observer.stop()
	print("Observer stopped!")


class ReloadHandler(FileSystemEventHandler):
		def on_modified(self, event):
			print("Modified: %s" % event)

		def on_created(self, event):
			print("Created: %s" % event)

		def on_deleted(self, event):
			print("Deleted: %s" % event)

class Fl0w:
	def __init__(self):
		self.window = None
		self.main_menu = Items()
		self.link_menu = Items()
		#self.link_menu.add_item(Item("Compile", action=self.info))
		self.main_menu.add_item(Item("Connect", "Connect to a fl0w server", action=self.invoke_connect))
		#self.main_menu.add_item(Item("Set Link", items=self.link_menu))
		

	# Input invokers
	def invoke_connect(self):
		Input("Address Port", on_done=self.connect).invoke(self.window)

	def invoke_auth(self):
		Input("Username Password", on_done=self.auth).invoke(self.window)


		

	def connect(self, connect_pair):
		connect_pair = connect_pair.split(" ")
		if len(connect_pair) == 2:
			try:
				self.sock = ESock(socket.create_connection(connect_pair))
				self.main_menu.add_item(Item("Auth", "Authenticate", action=self.invoke_auth))
			except Exception as e:
				sublime.error_message("Error during connection creation:\n %s" % str(e))
		else:
			sublime.error_message("Input does not consist of IP and port")

	def auth(self, auth_pair):
		auth_pair = auth_pair.split(" ")
		if len(auth_pair) == 2:
			pass
		"""
		self.main_menu.add_item(Item("Compile", action=self.info))
		self.main_menu.add_item(Item("Resync", action=self.info))
		self.main_menu.add_item(Item("Disconnect", action=self.info))
		self.main_menu.add_item(Item("Backup", action=self.info))
		"""


class Fl0wCommand(sublime_plugin.WindowCommand):
	def run(self, menu=None, action=None): 
		if fl0w.window == None:
			fl0w.window = self.window
		fl0w.main_menu.invoke(self.window)



fl0w = Fl0w()
observer = Observer()
observer.schedule(ReloadHandler(), path=".", recursive=True)
#observer.start()
