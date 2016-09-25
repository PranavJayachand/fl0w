import Logging
import Routing
import Config

#from .AsyncServer import Server
from .Broadcast import Broadcast

import json
import os
import subprocess
import re
import platform
import struct
from subprocess import Popen, PIPE

from wsgiref.simple_server import make_server
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication

from Highway import Server

"""
WALLABY_SYNC_ROUTE = "w_sync"
SUBLIME_SYNC_ROUTE = "s_sync"
"""

class Info(Routing.ServerRoute):
	def run(self, data, handler):
		handler.send({"editor" : len(handler.broadcast.channels[Handler.Channels.EDITOR]),
			"wallaby" : len(handler.broadcast.channels[Handler.Channels.WALLABY]),
			"routes" : list(handler.routes.keys())}, "info")


class Compile:
	REQUIRED = [Routing.ROUTE]
	HAS_MAIN = re.compile(r"\w*\s*main\(\)\s*(\{|.*)$")

	@staticmethod
	def is_valid_c_program(path):
		for line in open(path, "r").read().split("\n"):
			if Compile.HAS_MAIN.match(line):
				return True
		return False


	def __init__(self, source_path, binary_path):
		self.source_path = os.path.abspath(source_path) + "/"
		self.binary_path = os.path.abspath(binary_path) + "/"
		self.wallaby_library_avaliable = os.path.isfile("/usr/local/lib/libaurora.so") and os.path.isfile("/usr/local/lib/libdaylite.so")
		if not self.wallaby_library_avaliable:
			Logging.warning("Wallaby library not found. All Wallaby functions are unavaliable.")
		if platform.machine() != "armv7l":
			Logging.warning("Wrong processor architecture! Generated binaries will not run on Wallaby Controllers.")


	def compile(self, path, relpath, handler=None):
		if relpath.endswith(".c") and Compile.is_valid_c_program(path + relpath):
			name = "-".join(relpath.split("/")).rstrip(".c")
			full_path = self.binary_path + name
			if not os.path.exists(full_path):
				os.mkdir(full_path)
			error = True
			command = ["gcc", "-pipe", "-O0", "-lwallaby", "-I%s" % self.source_path, "-o", "%s" % full_path + "/botball_user_program", path + relpath]
			if not self.wallaby_library_avaliable:
				del command[command.index("-lwallaby")]
			p = Popen(command, stdout=PIPE, stderr=PIPE)
			error = False if p.wait() == 0 else True
			result = ""
			for line in p.communicate():
				result += line.decode()
			if handler != None:
				handler.send({"failed" : error, "returned" : result, "relpath" : relpath}, self.route)



class StdStream(Routing.ServerRoute):
	def __init__(self):
		self.stream_to = {}

	def run(self, data, handler):
		if type(data) is str:
			if handler in self.stream_to.keys():
				self.stream_to[handler].send(data, "std_stream")
		elif type(data) is dict:
			if handler in self.stream_to.keys():
				self.stream_to[handler].send(data, "std_stream")
				del self.stream_to[handler]



class GetInfo(Routing.ServerRoute):
	EDITOR = "e"
	WALLABY = "w"

	def run(self, data, handler):
		if "type" in data:
			if data["type"] == GetInfo.EDITOR:
				handler.channel = Handler.Channels.EDITOR
				handler.broadcast.add(handler, handler.channel)
			elif data["type"] == GetInfo.WALLABY:
				handler.channel = Handler.Channels.WALLABY
				handler.broadcast.add(handler, handler.channel)
		if "name" in data:
			handler.name = data["name"]
		Logging.info("'%s:%d' has identified as a %s client." % (handler.info[0], handler.info[1],
			"Editor" if handler.channel == Handler.Channels.EDITOR else
			"Wallaby" if handler.channel == Handler.Channels.WALLABY else
			"Unknown (will not subscribe to broadcast)"))

	def start(self, handler):
		handler.send(None, handler.reverse_routes[self])


class Handler(Server):
	class Channels:
		EDITOR = 1
		WALLABY = 2

	def setup(self, routes, broadcast, compression_level, debug=False):
		super().setup(routes, compression_level, debug=debug)
		self.broadcast = broadcast
		self.channel = None
		self.name = "Unknown"


	def ready(self):
		Logging.info("Handler for '%s:%d' ready." % (self.address, self.port))


	def closed(self, code, reason):
		if self.channel != None:
			self.broadcast.remove(self, self.channel)
		Logging.info("'%s:%d' disconnected." % (self.address, self.port))



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
config.add(Config.Option("compression_level", 0, validator=lambda x: x >= 0 and x <= 9))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	config = config.read_from_file(CONFIG_PATH)


broadcast = Broadcast()
# Populating broadcast channels with all channels defined in Handler.Channels
for channel in Handler.Channels.__dict__:
	if not channel.startswith("_"):
		broadcast.add_channel(Handler.Channels.__dict__[channel])

compile = Compile(config.source_path, config.binary_path)


server = make_server(config.server_address[0], config.server_address[1], 
	server_class=WSGIServer, handler_class=WebSocketWSGIRequestHandler, 
	app=WebSocketWSGIApplication(handler_cls=Handler, 
		handler_args={"debug" : config.debug, "broadcast" : broadcast, 
		"compression_level" : config.compression_level,
		"routes" : {"info" : Info(),
		"get_info" : GetInfo(), 
		"std_stream" : StdStream()}}))
server.initialize_websockets_manager()

try:
	server.serve_forever()
except KeyboardInterrupt:
	Logging.header("Gracefully shutting down server.")
	server.server_close()
	Logging.success("Server shutdown successful.")
