from sys import path
import os
import _thread
from time import strftime

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

from Highway import Client
import Routing

from SublimeMenu import *
import Logging

import webbrowser

CHANNEL = 1

def plugin_unloaded():
	for window in windows:
		if hasattr(window, "fl0w") and window.fl0w.connected:
			window.fl0w.invoke_disconnect()



class Fl0wClient(Client):
	def setup(self, routes, fl0w, debug=False):
		super().setup(routes, debug=debug)
		self.fl0w = fl0w


	def ready(self):
		self.fl0w.connected = True
		Logging.info("Connection ready!")


	def closed(self, code, reason):
		self.fl0w.connected = False
		Logging.info("Connection closed: %s (%s)" % (reason, code))


	class Info(Routing.ClientRoute):
		def run(self, data, handler):
			info = ""
			for key in data:
				info += "%s: %s\n" % (key.capitalize(), ", ".join(data[key]))
			sublime.message_dialog(info)
			handler.fl0w.invoke_main_menu()





class Fl0w:
	def __init__(self, window):
		self.connected = False
		self.window = window
		self.folder = window.folders()[0]


		self.start_menu = Menu()
		self.start_menu.add(Entry("Connect", "Connect to a fl0w server", action=self.invoke_connect))
		self.start_menu.add(Entry("About", "Information about fl0w", action=self.invoke_about))

		self.main_menu = Menu()
		#self.main_menu.add(Entry("Wallaby Control", "Control a connected Wallaby", action=self.invoke_wallaby_control))
		self.main_menu.add(Entry("Info", "Server info", action=lambda: self.ws.send(None, "info")))
		#self.main_menu.add(Entry("Debug", "Debug options", action=self.invoke_debug_options))
		self.main_menu.add(Entry("Disconnect", "Disconnect from server", action=self.invoke_disconnect))


	def invoke_start_menu(self):
		self.start_menu.invoke(self.window)


	def invoke_main_menu(self):
		self.main_menu.invoke(self.window)


	def invoke_about(self):
		if sublime.ok_cancel_dialog("fl0w by @robot0nfire", "robot0nfire.com"):
			webbrowser.open("http://robot0nfire.com")



	def connect(self, connect_details):
		compression_level = int(sublime.load_settings("fl0w.sublime-settings").get("compression_level"))
		try:
			self.ws = Fl0wClient('ws://%s' % connect_details)
			self.ws.setup({"info" : Fl0wClient.Info()}, self, debug=False)
			self.ws.connect()
			sublime.set_timeout_async(self.ws.run_forever, 0)
		except OSError as e:
			sublime.error_message("Error during connection creation:\n %s" % str(e))



	def invoke_connect(self):
		# Will be removed once autoconnect works
		self.connect("127.0.0.1:3077")


	def invoke_disconnect(self):
		if self.connected:
			self.ws.close()
			sublime.message_dialog("Connection closed ('%s')" % self.folder)





class Fl0wCommand(sublime_plugin.WindowCommand):
	def run(self):
		valid_window_setup = True
		folder_count = len(self.window.folders())
		if folder_count > 1:
			sublime.error_message("Only one open folder per window is allowed.")
			valid_window_setup = False
		elif folder_count == 0:
			sublime.error_message("No folder open in window.")
			valid_window_setup = False
		if valid_window_setup:
			if not hasattr(self.window, "fl0w"):
				folder = self.window.folders()[0]
				files = os.listdir(folder)
				if not ".no-fl0w" in files:
					if not ".fl0w" in files:
						open(folder + "/.fl0w", 'a').close()
						self.window.fl0w = Fl0w(self.window)
						windows.append(self.window)
						self.window.fl0w.start_menu.invoke(self.window)
					else:
						self.window.fl0w = Fl0w(self.window)
						windows.append(self.window)
						self.window.fl0w.start_menu.invoke(self.window)
				else:
					sublime.error_message("fl0w can't be opened in your current directory (.no-fl0w file exists)")
			else:
				if not self.window.fl0w.connected:
					self.window.fl0w.invoke_start_menu()
				else:
					self.window.fl0w.invoke_main_menu()
		else:
			if hasattr(self.window, "fl0w"):
				sublime.error_message("Window setup was invalidated (Don't close or open any additional folders in a fl0w window)")
				if self.window.fl0w.connected:
					self.window.fl0w.invoke_disconnect()



windows = []
