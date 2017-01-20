from sys import path
import os
from time import strftime
from functools import partial
import re

fl0w_path = os.path.dirname(os.path.realpath(__file__))
shared_path = os.path.dirname(os.path.realpath(__file__)) + "/Shared/"
if fl0w_path not in path:
	path.append(fl0w_path)
if shared_path not in path:
	path.append(shared_path)


import sublime
import sublime_plugin

from Highway import Client, Route, Pipe, DummyPipe
from Utils import get_hostname

from SublimeMenu import *
import Logging

import webbrowser
from time import sleep
import os

CHANNEL = 1
FL0W_STATUS = "fl0w"

def plugin_unloaded():
	for window in windows:
		if hasattr(window, "fl0w") and window.fl0w.connected:
			window.fl0w.invoke_disconnect()
			for sensor_type in ("analog", "digital"):
				window.active_view().erase_phantoms(sensor_type)


PARENTHESES_REGEX = re.compile("\((.*?)\)")
STYLE_OPEN = "<body><style>code { color: var(--orangish); }</style><code>"
STYLE_CLOSE = "</code></body>"

ERROR_OPEN = "<body><style>code { color: var(--redish); }</style><code>"
ERROR_CLOSE = "</code></body>"

windows = []
sensor_phantoms = []

def set_status(status, window):
	window.active_view().set_status(FL0W_STATUS, 
				"fl0w: %s" % status)

class Fl0wClient(Client):
	def setup(self, routes, fl0w, debug=False):
		super().setup(routes, debug=debug)
		self.fl0w = fl0w


	def ready(self):
		self.fl0w.connected = True
		if self.fl0w.debug:
			Logging.info("Connection ready!")
		# Enlist on editor channel
		self.send({"channel" : 1, "name" : get_hostname()}, "subscribe")
		# Subscribe to controller channel
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


	class Sensor(Pipe):
		def run(self, data, peer, handler):
			for sensor_phantom in handler.fl0w.subscriptions:
				sensor_phantom.update_sensor_values(data)


	class Peers(Route):
		def start(self, handler):
			self.selected_action_menu = None

		def run(self, data, handler):
			handler.fl0w.controller_menu.clear()
			for id_ in data:
				action_menu = Menu()
				action_menu.id_ = id_
				action_menu += Entry("Set Target", 
					"Set controller as target for program execution and sensor readouts.", 
					action=partial(lambda handler, id_: self.set_target(handler, id_), 
						handler, id_)) 				
				action_menu += Entry("Programs", 
					"Lists all executable programs on the controller.", 
					action=partial(lambda handler, id_: handler.pipe(None, "list_programs", id_), 
						handler, id_))          
				action_menu += Entry("Set Name", 
					"Sets the hostname of the selected controller",
					action=partial(lambda handler, id_: Input("New Hostname:", initial_text=data[id_]["name"], 
						on_done=lambda hostname: handler.pipe(
							{"set" : hostname}, "hostname", id_)).invoke(handler.fl0w.window), handler, id_))
				action_menu += Entry("Processes", 
					"Lists processes currently running on controller.", 
					action=partial(lambda handler, id_: handler.pipe(None, "processes", id_), 
						handler, id_))
				action_menu += Entry("Identify", 
					"Plays an identification sound on the controller.", 
					action=partial(lambda handler, id_: handler.pipe(None, "identify", id_), 
						handler, id_))
				action_menu.back = handler.fl0w.controller_menu
				handler.fl0w.controller_menu += Entry(data[id_]["name"], id_, sub_menu=action_menu,
					action=self.set_selected_action_menu,
					kwargs={"selected_action_menu" : action_menu})


		def set_target(self, handler, peer):
			handler.fl0w.target = peer
			if handler.fl0w.debug:
				set_status("Target: %s" % peer, handler.fl0w.window)


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

	class StdStream(Pipe):
		def run(data, peer, handler):
			pass



class Fl0w:
	def __init__(self, window, debug=False):
		self.window = window
		self.folder = window.folders()[0]
		if self.folder != "/":
			self.folder = self.folder + "/"

		self.connected = False
		
		self.subscriptions = {}
		self._combined_subscriptions = {"analog" : [], "digital" : []}
		
		self._target = None
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
		self.main_menu += Entry("Controllers", "All connected controllers", 
			sub_menu=self.controller_menu)
		self.main_menu += Entry("Settings", "General purpose settings", 
			sub_menu=self.settings)
		self.main_menu += Entry("Disconnect", "Disconnect from server", 
			action=self.invoke_disconnect)

		# Patch all sensor phantom that have been created before a fl0w instance
		# was attached to the window
		for sensor_phantom in sensor_phantoms:
			if sensor_phantom.window.id() == self.window.id():
				sensor_phantom.fl0w = self
				if self.debug:
					Logging.info("Patched sensor phantom '%s'" % str(sensor_phatom))


	@property
	def target(self):
		return self._target


	@target.setter
	def target(self, target):
		if self.target != None:
			self.ws.pipe("unsubscribe", "sensor", self.target)
		self._target = target
		set_status("Set target: %s" % target, self.window)
		if self.combined_subscriptions != {"analog" : [], "digital" : []}:
			self.ws.pipe({"subscribe" : self.combined_subscriptions_}, "sensor", target)


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
		set_status("Debug set to %s" % self._debug, self.window)


	@property
	def combined_subscriptions(self):
		return self._combined_subscriptions


	@combined_subscriptions.setter
	def combined_subscriptions(self, combined_subscriptions_):
		if self.combined_subscriptions != combined_subscriptions_:
			self._combined_subscriptions = combined_subscriptions_
			if self.connected and self.target != None:
				self.ws.pipe("unsubscribe", "sensor", self.target)
				self.ws.pipe({"subscribe" : combined_subscriptions_}, "sensor",
					self.target)


	def subscribe(self, sensor_phatom, subscriptions):
		self.subscriptions[sensor_phatom] = subscriptions
		self.make_subscriptions()



	def unsubscribe(self, sensor_phantom):
		if sensor_phantom in self.subscriptions:
			del self.subscriptions[sensor_phantom]
		self.make_subscriptions()


	def make_subscriptions(self):
		combined_subscriptions = {"analog" : [], "digital" : []}
		for sensor_phantom in self.subscriptions:
			for sensor_type in ("analog", "digital"):
				combined_subscriptions[sensor_type] = list(
						set(combined_subscriptions[sensor_type]) | 
						set(self.subscriptions[sensor_phantom][sensor_type])
					)
		self.combined_subscriptions = combined_subscriptions


	def run_program(self, path):
		if self.connected and self.target != None:
			relpath = os.path.relpath(path, self.folder)
			if os.path.isfile(self.folder + relpath):
				if self.debug:
					Logging.info("Running program '%s'" % relpath)
				self.ws.pipe(relpath, "run_program", self.target)


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
				"list_programs" : Fl0wClient.ListPrograms(), "sensor" : Fl0wClient.Sensor()}, 
				self, debug=True)
			self.ws.connect()
			sublime.set_timeout_async(self.ws.run_forever, 0)
			set_status("Connection opened '%s'" % self.folder, self.window)
			self.connected = True
		except OSError as e:
			sublime.error_message("Error during connection creation:\n %s" % str(e))



	def invoke_connect(self):
		# Will be removed once autoconnect works
		self.connect("127.0.0.1:3077")


	def invoke_disconnect(self):
		if self.connected:
			for sensor_phantom in sensor_phantoms:
				if sensor_phantom.window.id() == self.window.id():
					sensor_phantom.enabled = False
			self.ws.close()
			set_status("Connection closed '%s'" % self.folder, self.window)
			self.connected = False


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


class RunCommand(sublime_plugin.WindowCommand):
	def run(self):
		if hasattr(self.window, "fl0w"):
			if self.window.fl0w.connected:
				if self.window.fl0w.target == None:
					sublime.error_message("A target controller has to be set to "
						"run programs.")
				else:
					file_name = self.window.active_view().file_name()
					if file_name != None and file_name.endswith(".c"):
						self.window.fl0w.run_program(file_name)
			else:
				sublime.error_message("fl0w is not connected.")
		else:
			sublime.error_message("fl0w is not running in your current window.")


class SensorCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		super().__init__(window)
		self.enabled = False


	def run(self):
		if not self.enabled:
			if hasattr(self.window, "fl0w"):
				if self.window.fl0w.connected:
					if self.window.fl0w.target == None:
						sublime.error_message("A target controller has to be set to "
							"enable inline sensor readouts.")
					else:
						self.enabled = not self.enabled
						for sensor_phantom in sensor_phantoms:
							if sensor_phantom.window.id() == self.window.id():
								sensor_phantom.enabled = self.enabled
						set_status("Enabled sensor phantoms.", self.window)
				else:
					sublime.error_message("fl0w is not connected.")
			else:
				sublime.error_message("fl0w is not running in your current window.")
		else:
			self.enabled = not self.enabled
			for sensor_phantom in sensor_phantoms:
				if sensor_phantom.window.id() == self.window.id():
					sensor_phantom.enabled = self.enabled
			set_status("Disabled sensor phantoms.", self.window)


class SensorPhantom(sublime_plugin.ViewEventListener):
	def __init__(self, view):
		self.view = view
		self.window = view.window()
		
		# Is patched by the fl0w instance that is in control of the same window
		self.fl0w = None
		self._enabled = False

		self._matches = {"analog" : [], "digital" : []}

		self.timeout_scheduled = False
		self.needs_update = False

		for window in windows:
			if hasattr(window, "fl0w"):
				self.fl0w = window.fl0w
		if not self in sensor_phantoms:
			sensor_phantoms.append(self)


	@property
	def enabled(self):
		return self._enabled

			
	@enabled.setter
	def enabled(self, enabled_):
		self._enabled = enabled_
		if enabled_:
			if self.fl0w != None:
				self.find_matches()
				self.fl0w.subscribe(self, self.subscriptions)
		else:
			if self.fl0w != None:
				self.fl0w.unsubscribe(self)
			for sensor_type in ("analog", "digital"):
				self.window.active_view().erase_phantoms(sensor_type)


	@property
	def matches(self):
		return self._matches

	@matches.setter
	def matches(self, matches_):
		if not matches_ == self.matches:
			self._matches = matches_
			self.fl0w.subscribe(self, self.subscriptions)


	@property
	def subscriptions(self):
		subscriptions_ = {"analog" : [], "digital" : []}
		for sensor_type in ("analog", "digital"):
			subscriptions_[sensor_type] = [sensor[0] for sensor in self.matches[sensor_type]]
		return subscriptions_


	def find_matches(self):
		matches = {"analog" : [], "digital" : []}
		# Don't do any calculations on 1MB or larger files
		if self.view.size() < 2**20:
			for method_name in ("analog", "digital"):
				candidates = self.view.find_all("%s\(\d*\)" % method_name)
				for candidate in candidates:
					line = self.view.substr(candidate)
					port_candidates = re.findall(PARENTHESES_REGEX, line)
					if len(port_candidates) == 1:
						if port_candidates[0].isnumeric():
							matches[method_name].append(
								(
									int(port_candidates[0]), 
									sublime.Region(self.view.line(candidate.a).b)
								))
		self.matches = matches

	# Called by fl0w instance
	def update_sensor_values(self, readouts):
		for sensor_type in ("analog", "digital"):
			self.view.erase_phantoms(sensor_type)
			for match in self.matches[sensor_type]:
				try:
					self.view.add_phantom(sensor_type, match[1], 
						STYLE_OPEN + str(readouts[sensor_type][str(match[0])]) + STYLE_CLOSE, 
						sublime.LAYOUT_INLINE)
				except KeyError:
					self.view.add_phantom(sensor_type, match[1], 
						ERROR_OPEN + "!" + ERROR_CLOSE, 
						sublime.LAYOUT_INLINE)


	def handle_timeout(self):
		self.timeout_scheduled = False
		if self.needs_update:
			self.needs_update = False
			self.find_matches()


	def on_modified(self):
		if self.enabled:
			if self.timeout_scheduled:
				self.needs_update = True
			else:
				sublime.set_timeout(lambda: self.handle_timeout(), 500)
				self.find_matches()


	def __del__(self):		
		self.enabled = False
		if self in sensor_phantoms:
			del sensor_phantoms[sensor_phantoms.index(self)]
