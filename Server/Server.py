import Logging
import Routing
import Config

from Sync import SyncServer

from .AsyncServer import Server
from .Broadcast import Broadcast

import json
import os
import subprocess
import re
from subprocess import Popen, PIPE


WALLABY_SYNC_ROUTE = "w_sync"
SUBLIME_SYNC_ROUTE = "s_sync"


class Info(Routing.ServerRoute):
	def run(self, data, handler):
		handler.sock.send("Connected ST clients: %d\nConnected Wallabies: %d\nAvaliable routes: %s" % (
			len(handler.broadcast.channels[Handler.Channels.SUBLIME]),
			len(handler.broadcast.channels[Handler.Channels.WALLABY]), 
			", ".join([route for route in list(handler.routes.keys())])), "info")


class StdStream(Routing.ServerRoute):
	def __init__(self):
		self.stream_to = {}

	def run(self, data, handler):
		if type(data) is str:
			if handler in self.stream_to.keys():
				self.stream_to[handler].sock.send(data, "std_stream")
		elif type(data) is dict:
			if handler in self.stream_to.keys():
				self.stream_to[handler].sock.send(data, "std_stream")
				del self.stream_to[handler]



class WallabyControl(Routing.ServerRoute):
	def __init__(self):
		self.actions_with_params = {"run" : self.run_program}
		self.actions_without_params = {"restart" : self.restart, "disconnect" : self.disconnect, 
		"reboot" : self.reboot, "shutdown" : self.shutdown, "stop" : self.stop_programs}
		self.programs = []


	def run(self, data, handler):
		self.programs = []
		for program in os.listdir(handler.routes[WALLABY_SYNC_ROUTE].folder):
			if os.path.isdir(handler.routes[WALLABY_SYNC_ROUTE].folder + program):
				if "botball_user_program" in os.listdir(handler.routes[WALLABY_SYNC_ROUTE].folder + program):
					self.programs.append(program)
		if data == "list_wallaby_controllers":
			wallaby_controllers = {}
			for wallaby_handler in handler.broadcast.channels[Handler.Channels.WALLABY]:
				wallaby_controllers["%s:%d" % (wallaby_handler.sock.address, wallaby_handler.sock.port)] = wallaby_handler.name
			handler.sock.send({"wallaby_controllers" : wallaby_controllers}, "wallaby_control")
		elif data == "list_programs":
			handler.sock.send({"programs" : self.programs}, "wallaby_control")
		elif type(data) is dict:
			for wallaby_handler in handler.broadcast.channels[Handler.Channels.WALLABY]:
				address_pair = "%s:%d" % (wallaby_handler.sock.address, wallaby_handler.sock.port)
				if address_pair in data.keys():
					if type(data[address_pair]) is list:
						for action in data[address_pair]:
							if action in self.actions_without_params.keys():
								self.actions_without_params[action](wallaby_handler, handler)
					elif type(data[address_pair]) is dict:
						for action in data[address_pair]:
							if action in self.actions_with_params.keys():
								self.actions_with_params[action](data[address_pair][action], wallaby_handler, handler)
					return
			handler.sock.send("Wallaby not connected anymore.", "error_report")


	def restart(self, wallaby_handler, handler):
		wallaby_handler.sock.send("restart", "wallaby_control")


	def disconnect(self, wallaby_handler, handler):
		pass


	def reboot(self, wallaby_handler, handler):
		wallaby_handler.sock.send("reboot", "wallaby_control")


	def shutdown(self, wallaby_handler, handler):
		wallaby_handler.sock.send("shutdown", "wallaby_control")


	def run_program(self, program, wallaby_handler, handler):
		handler.routes["std_stream"].stream_to.update({wallaby_handler : handler})
		wallaby_handler.sock.send({"run" : program}, "wallaby_control")		


	def stop_programs(self, wallaby_handler, handler):
		wallaby_handler.sock.send("stop", "wallaby_control")


class Compile(Routing.ServerRoute):
	REQUIRED = [Routing.ROUTE]
	HAS_MAIN = re.compile(r"\w*\s*main\(\)\s*(\{|.*)$")

	@staticmethod
	def is_valid_c_program(path):
		for line in open(path, "r").read().split("\n"):
			if Compile.HAS_MAIN.match(line):
				return True
		return False


	def __init__(self, binary_path):
		self.binary_path = os.path.abspath(binary_path) + "/"


	def compile(self, path, relpath, handler=None):
		if relpath.endswith(".c") and Compile.is_valid_c_program(path + relpath):
			name = "-".join(relpath.split("/")).rstrip(".c")
			full_path = self.binary_path + name
			if not os.path.exists(full_path):
				os.mkdir(full_path)
			error = True
			p = Popen(["gcc", "-o", "%s" % full_path + "/botball_user_program", path + relpath], stdout=PIPE, stderr=PIPE)
			error = False if p.wait() == 0 else True
			result = ""
			for line in p.communicate():
				result += line.decode()
			if handler != None:
				handler.sock.send({"failed" : error, "returned" : result, "relpath" : relpath}, self.route)



class GetInfo(Routing.ServerRoute):
	REQUIRED = [Routing.ROUTE]

	SUBLIME_TEXT = "s"
	WALLABY = "w"

	def run(self, data, handler):
		if "type" in data:
			if data["type"] == GetInfo.SUBLIME_TEXT:
				handler.channel = Handler.Channels.SUBLIME
				handler.broadcast.add(handler, handler.channel)
			elif data["type"] == GetInfo.WALLABY:
				handler.channel = Handler.Channels.WALLABY
				handler.broadcast.add(handler, handler.channel)
		if "name" in data:
			handler.name = data["name"]
		Logging.info("'%s:%d' has identified as a %s client." % (handler.info[0], handler.info[1], 
			"Sublime Text" if handler.channel == Handler.Channels.SUBLIME else 
			"Wallaby" if handler.channel == Handler.Channels.WALLABY else 
			"Unknown (will not subscribe to broadcast)"))

	def start(self, handler):
		handler.sock.send("", self.route)


class Handler(Server.Handler):
	class Channels:
		SUBLIME = 1
		WALLABY = 2

	def setup(self, routes, broadcast):
		Logging.info("Handler for '%s:%d' initalised." % (self.sock.address, self.sock.port))
		self.broadcast = broadcast
		self.channel = None
		self.routes = Routing.create_routes(routes, self)
		self.name = "Unknown"

		
	def handle(self, data, route):
		if route in self.routes:
			self.routes[route].run(data, self)
		else:
			self.sock.send("Invalid route '%s'" % route, "error_report")


	def finish(self):
		if self.channel != None:
			self.broadcast.remove(self, self.channel)
		Logging.info("'%s:%d' disconnected." % (self.sock.address, self.sock.port))


	def __repr__(self):
		return "%s: %s:%d" % (self.name, self.sock.address, self.sock.port)


def folder_validator(folder):
	if not os.path.isdir(folder):
		try:
			os.mkdir(folder)
		except OSError:
			return False
	return True


CONFIG_PATH = "server.cfg"

config = Config.Config()
config.add(Config.Option("server_address", ("127.0.0.1", 3077)))
config.add(Config.Option("debug", True, validator=lambda x: True if True or False else False))
config.add(Config.Option("binary_path", "Binaries", validator=folder_validator))
config.add(Config.Option("source_path", "Source", validator=folder_validator))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	config = config.read_from_file(CONFIG_PATH)

server = Server(config.server_address, debug=config.debug)

broadcast = Broadcast()
# Populating broadcast channels with all channels defined in Handler.Channels
for channel in Handler.Channels.__dict__:
	if not channel.startswith("_"):
		broadcast.add_channel(Handler.Channels.__dict__[channel])

compile = Compile(config.binary_path)
w_sync = SyncServer(config.binary_path, Handler.Channels.WALLABY, debug=config.debug, deleted_db_path="deleted-w.pickle")
s_sync = SyncServer(config.source_path, Handler.Channels.SUBLIME, debug=config.debug, deleted_db_path="deleted-s.pickle", modified_hook=compile.compile)

try:
	Logging.header("fl0w server started on '%s:%d'" % (config.server_address[0], config.server_address[1]))
	server.run(Handler, 
		{"broadcast" : broadcast,
		"routes" : {"info" : Info(), "wallaby_control" : WallabyControl(), 
		"get_info" : GetInfo(), "compile" : compile, "std_stream" : StdStream(),
		WALLABY_SYNC_ROUTE : w_sync,
		SUBLIME_SYNC_ROUTE : s_sync}})
except KeyboardInterrupt:
	Logging.header("Gracefully shutting down server.")
	w_sync.stop()
	s_sync.stop()
	server.stop()
	Logging.success("Server shutdown successful.")
