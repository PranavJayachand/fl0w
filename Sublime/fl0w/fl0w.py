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

import webbrowser

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
		self.connected = False

		self.window = None
		self.start_menu = Items()
		self.start_menu.add_item(Item("Connect", "Connect to a fl0w server", action=self.invoke_connect))
		self.start_menu.add_item(Item("About", "Information about fl0w", action=self.invoke_about))
		self.main_menu = Items()
		self.main_menu.add_item(Item("Info", "Server info", action=self.invoke_info))
		self.main_menu.add_item(Item("Disconnect", "Disconnect from server", action=self.invoke_disconnect))

		

	# Input invokers
	def invoke_connect(self):
		Input("Address:Port", initial_text="", on_done=self.connect).invoke(self.window)

	def invoke_about(self):
		if sublime.ok_cancel_dialog("fl0w by @robot0nfire", "robot0nfire.com"):	
			webbrowser.open("http://robot0nfire.com")

	def invoke_info(self):
		self.sock.send({"info" : ""})
		sublime.message_dialog(self.sock.recv())
		self.sock.send("")
		sublime.message_dialog(self.sock.recv())

	def invoke_disconnect(self):
		self.sock.close()
		self.connected = False
		sublime.message_dialog("Connection closed")


	def connect(self, connect_details):
		connect_details = connect_details.split(":")
		if len(connect_details) == 2:
			try:
				self.sock = ESock(socket.create_connection((connect_details[0], int(connect_details[1]))))
				sublime.status_message("Connected to %s:%s." % (connect_details[0], connect_details[1]))
				self.connected = True
			except Exception as e:
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
