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
import Routing
from SublimeMenu import *

import webbrowser

def plugin_unloaded():
	observer.stop()
	try:
		fl0w.invoke_disconnect()
	except:
		pass
	print("Observer stopped!")



def sock_handler(sock, routes, handler):
	sock.send("st", "set_type")
	while 1:
		try:
			data = sock.recv()
			if data[1] in routes:
				routes[data[1]].run(data[0], handler)
		except (OSError, socket.error):
			handler.invoke_disconnect()
			break


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

		self.start_menu = Menu()
		self.start_menu.add(Entry("Connect", "Connect to a fl0w server", action=self.invoke_connect))
		self.start_menu.add(Entry("About", "Information about fl0w", action=self.invoke_about))
		self.main_menu = Menu()
		self.main_menu.add(Entry("Wallaby Control", "Control a connected Wallaby", action=self.invoke_wallaby_control))
		self.main_menu.add(Entry("Info", "Server info", action=self.invoke_info))
		self.main_menu.add(Entry("Debug", "Toggle debug levels", action=self.invoke_debug_level))
		self.main_menu.add(Entry("Disconnect", "Disconnect from server", action=self.invoke_disconnect))

	
	class ErrorReport(Routing.ClientRoute):
		def run(self, data, handler):
			sublime.error_message(data)


	# Input invokers
	def invoke_connect(self):
		address = sublime.load_settings("fl0w.sublime-setting").get("server_address")
		address = "" if type(address) is not str else address
		Input("Address:Port", initial_text=address, on_done=self.connect).invoke(self.window)

	def invoke_about(self):
		if sublime.ok_cancel_dialog("fl0w by @robot0nfire", "robot0nfire.com"):	
			webbrowser.open("http://robot0nfire.com")

	def invoke_wallaby_control(self):
		self.sock.send("list", "wallaby_control")


	class WallabyControl(Routing.ClientRoute):
		def run(self, data, handler):
			wallaby_menu = Menu(subtitles=False)
			entry_count = 0
			for wallaby in data:
				wallaby_menu.add(Entry(wallaby, action=handler.wallaby_control_submenu, kwargs={"wallaby" : wallaby}))
				entry_count += 1
			if entry_count != 0:
				wallaby_menu.invoke(handler.window, back=handler.main_menu)
			else:
				sublime.error_message("No Wallabies connected.")


	def wallaby_control_submenu(self, wallaby):
		menu = Menu(subtitles=False)
		for command in ("Stop", "Restart", "Reboot", "Disconnect"):
			menu.add(Entry(command, action=self.sock.send, kwargs={"data" : {wallaby : command.lower()}, "route" : "wallaby_control"}))
		menu.invoke(self.window)


	def invoke_debug_level(self):
		debug_menu = Menu(subtitles=False)
		debug_menu.add(Entry("On", action=self.set_debug, kwargs={"debug" : True}))
		debug_menu.add(Entry("Off", action=self.set_debug, kwargs={"debug" : False}))
		debug_menu.invoke(self.window, back=self.main_menu)


	def set_debug(self, debug):
		print("Debug now %s" % debug)
		self.sock.debug = debug


	def invoke_info(self):
		self.sock.send("", "info")

	class Info(Routing.ClientRoute):
		def run(self, data, handler):
			sublime.message_dialog(data)
			handler.main_menu.invoke(handler.window)



	def invoke_disconnect(self):
		self.sock.close()
		if self.connected:
			sublime.message_dialog("Connection closed")
		self.connected = False



	def connect(self, connect_details):
		connect_details_raw = connect_details
		connect_details = connect_details.split(":")
		if len(connect_details) == 2:
			try:
				self.sock = ESock(socket.create_connection((connect_details[0], int(connect_details[1]))), disconnect_callback=self.invoke_disconnect)
				sublime.status_message("Connected to %s:%s." % (connect_details[0], connect_details[1]))
				self.connected = True
				_thread.start_new_thread(sock_handler, (self.sock, {"error_report": Fl0w.ErrorReport(), "info" : Fl0w.Info(), "wallaby_control" : Fl0w.WallabyControl()}, self))
				sublime.load_settings("fl0w.sublime-setting").set("server_address", connect_details_raw)
				sublime.save_settings("fl0w.sublime-setting")
				self.main_menu.invoke(self.window)
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
