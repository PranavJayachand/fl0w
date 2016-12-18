from sys import path
import os
import _thread
from time import strftime
from functools import partial

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

from Highway import Client, Route, Pipe, DummyPipe

from SublimeMenu import *
import Logging

import webbrowser

CHANNEL = 1
FL0W_STATUS = "fl0w"

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
		if self.fl0w.debug:
			Logging.info("Connection ready!")
		self.send({"subscribe" : [2]}, "peers")


	def closed(self, code, reason):
		self.fl0w.connected = False
		if self.fl0w.debug:
			Logging.info("Connection closed: %s (%s)" % (reason, code))


	def peer_unavaliable(self, peer):
		sublime.error_message("The specifed controller is not connected anymore.")


	class Info(Route):
		def run(self, data, handler):
			info = ""
			for key in data:
				info += "%s: %s\n" % (key.capitalize(), ", ".join(data[key]))
			sublime.message_dialog(info)
			handler.fl0w.meta.invoke(handler.fl0w.window, back=handler.fl0w.main_menu)


	class Peers(Route):
		def start(self, handler):
			self.selected_action_menu = None

		def run(self, data, handler):
			handler.fl0w.controller_menu.clear()
			for id_ in data:
				action_menu = Menu()
				print(id(action_menu))
				action_menu.id_ = id_
				action_menu += Entry("Programs", 
					"Lists all executable programs on the controller.", 
					action=partial(lambda handler, id_: handler.pipe(None, "list_programs", id_), 
						handler, id_))				
				action_menu += Entry("Set Name", 
					"Sets the hostname of the selected controller",
					action=lambda: Input("New Hostname:", initial_text=data[id_]["name"], 
					on_done=lambda hostname: handler.pipe({"set" : hostname}, 
						"hostname", id_)).invoke(handler.fl0w.window))
				action_menu += Entry("Processes", 
					"Lists processes currently running on controller.", 
					action=partial(lambda handler: handler.pipe(None, "processes", id_), 
						handler, id_))
				action_menu.back = handler.fl0w.controller_menu
				handler.fl0w.controller_menu += Entry(data[id_]["name"], id_, sub_menu=action_menu,
					action=self.set_selected_action_menu,
					kwargs={"selected_action_menu" : action_menu})


		def set_selected_action_menu(self, selected_action_menu):
			self.selected_action_menu = selected_action_menu


	class Processes(Pipe):
		def run(self, data, peer, handler):
			view = handler.fl0w.window.new_file()
			view.set_name("Processes")
			view.settings().set("draw_indent_guides", False)
			for line in data:
				view.run_command("append", {"characters": line + "\n"})
			view.set_read_only(True)


	class ListPrograms(Pipe):
		def run(self, data, peer, handler):
			program_menu = Menu(subtitles=False)
			for program in data:
				program_menu += Entry(program, 
					action=lambda handler: handler.pipe(program, 
						"run_program", 
						handler.routes["peers"].selected_action_menu.id_),
					kwargs={"handler" : handler})
			program_menu.invoke(handler.fl0w.window, 
				back=handler.routes["peers"].selected_action_menu)



class Fl0w:
	def __init__(self, window, debug=False):
		self.connected = False
		self.window = window
		self.folder = window.folders()[0]
		self._debug = debug


		self.start_menu = Menu()
		self.start_menu += Entry("Connect", "Connect to a fl0w server", 
			action=self.invoke_connect)
		self.start_menu += Entry("About", "Information about fl0w", 
			action=self.invoke_about)

		self.debug_menu = Menu(subtitles=False)
		self.debug_menu += Entry("On", 
			action=lambda: self.set_debug(True))
		self.debug_menu += Entry("Off", 
			action=lambda: self.set_debug(False))

		self.settings = Menu()
		self.settings += Entry("Debug", "Toggle debug mode", 
			sub_menu=self.debug_menu)

		self.meta = Menu()
		self.meta += Entry("Info", "Server info", 
			action=lambda: self.ws.send(None, "info"))
		self.meta_entry = Entry("Meta", "Debug information about fl0w", 
			sub_menu=self.meta)
		if self.debug:	
			self.main_menu += self.meta_entry
		
		
		self.main_menu = Menu()
		self.controller_menu = Menu()
		self.main_menu += Entry("Controllers", "All connected controllers.", 
			sub_menu=self.controller_menu)
		self.main_menu += Entry("Settings", "General purpose settings", 
			sub_menu=self.settings)
		self.main_menu += Entry("Disconnect", "Disconnect from server", 
			action=self.invoke_disconnect)
		

	@property
	def debug(self):
		return self._debug


	def set_debug(self, debug):
		self.debug = debug


	@debug.setter
	def debug(self, debug):
		if debug:
			self._debug = True
			if not self.meta_entry in self.main_menu.entries.values():
				self.main_menu += self.meta_entry
		else:
			self._debug = False
			self.main_menu -= self.meta_entry
		self.window.active_view().set_status(FL0W_STATUS, 
			"Debug set to %s" % self._debug)


	def invoke_start_menu(self):
		self.start_menu.invoke(self.window)


	def invoke_main_menu(self):
		self.main_menu.invoke(self.window)


	def invoke_about(self):
		if sublime.ok_cancel_dialog("fl0w by @robot0nfire", "robot0nfire.com"):
			webbrowser.open("http://robot0nfire.com")



	def connect(self, connect_details):
		try:
			self.ws = Fl0wClient('ws://%s' % connect_details)
			self.ws.setup({"info" : Fl0wClient.Info(), "peers" : Fl0wClient.Peers(),
				"processes" : Fl0wClient.Processes(), 
				"list_programs" : Fl0wClient.ListPrograms()}, 
				self, debug=True)
			self.ws.connect()
			sublime.set_timeout_async(self.ws.run_forever, 0)
			self.window.active_view().set_status(FL0W_STATUS, 
				"Connection opened '%s'" % self.folder)
		except OSError as e:
			sublime.error_message("Error during connection creation:\n %s" % str(e))



	def invoke_connect(self):
		# Will be removed once autoconnect works
		self.connect("127.0.0.1:3077")


	def invoke_disconnect(self):
		if self.connected:
			self.ws.close()
			self.window.active_view().set_status(FL0W_STATUS, 
				"Connection closed '%s'" % self.folder)





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
				self.window.fl0w.invoke_disconnect()



windows = []
