import Logging
import Routing
import Config

from Sync import SyncServer

from .AsyncServer import Server
from .Broadcast import Broadcast

from time import strftime
from time import time
import json
import os


class Info(Routing.ServerRoute):
	def run(self, data, handler):
		handler.sock.send("Start time: %s\nConnected ST clients: %d\nConnected Wallabies: %d\nAvaliable routes: %s" % (
			handler.start_time, len(handler.broadcast.channels[Handler.Channels.SUBLIME]),
			len(handler.broadcast.channels[Handler.Channels.WALLABY]), ", ".join([route for route in list(handler.routes.keys())])), "info")


class WallabyControl(Routing.ServerRoute):
	def run(self, data, handler):
		if data == "list":
			wallabies = []
			for wallaby in handler.broadcast.channels[Handler.Channels.WALLABY]:
				wallabies.append("%s:%d" % (wallaby.address, wallaby.port))
			handler.sock.send(wallabies, "wallaby_control")
		elif type(data) is dict:
			for wallaby in handler.broadcast.channels[Handler.Channels.WALLABY]:
				address_pair = "%s:%d" % (wallaby.address, wallaby.port)
				if address_pair in data.keys():
					if data[address_pair] in ("stop", "restart", "disconnect", "reboot", "shutdown"):
						wallaby.send(data[address_pair], "wallaby_control")
					elif type(data[address_pair]) is dict:
						if "run" in data[address_pair]:
							Logging.warning("Remote binary execution not yet implemented. (file_sync and compile required)")
					else:
						Logging.warning("'%s:%d' has issued an invalid control command." % (handler.info[0], handler.info[1]))
				return
			handler.sock.send("Wallaby not connected anymore.", "error_report")


class SetType(Routing.ServerRoute):
	def run(self, data, handler):
		if data == "st":
			handler.channel = Handler.Channels.SUBLIME
			handler.broadcast.add(handler, handler.channel)
		elif data == "w":
			handler.channel = Handler.Channels.WALLABY
			handler.broadcast.add(handler, handler.channel)
		else:
			handler.sock.close()
			return
		Logging.info("'%s:%d' has identified as a %s client." % (handler.info[0], handler.info[1], 
			"Sublime Text" if handler.channel == Handler.Channels.SUBLIME else 
			"Wallaby" if handler.channel == Handler.Channels.WALLABY else 
			"Unknown (will not subscribe to broadcast)"))


class GetInfo(Routing.ServerRoute):
	REQUIRED = [Routing.ROUTE]

	def run(self, data, handler):
		if "type" in data:
			if data["type"] == "st":
				handler.channel = Handler.Channels.SUBLIME
				handler.broadcast.add(handler, handler.channel)
			elif data["type"] == "w":
				handler.channel = Handler.Channels.WALLABY
				handler.broadcast.add(handler, handler.channel)
		if "name" in data:
			handler.sock.name = data["name"]
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
		self.start_time = time()
		self.name = "Unknown"
		for route in self.routes:
			self.routes[route].start(self)		

		
	def handle(self, data, route):
		if route in self.routes:
			self.routes[route].run(data, self)
		else:
			self.sock.send("Invalid route '%s'" % route, "error_report")


	def finish(self):
		if self.channel != None:
			self.broadcast.remove(self, self.channel)
		for route in self.routes:
			self.routes[route].stop(self)
		Logging.info("'%s:%d' disconnected." % (self.sock.address, self.sock.port))


def folder_validator(folder):
	if not os.path.isdir(folder):
		try:
			os.mkdir(folder)
		except OSError:
			return False
	return True


CONFIG_PATH = "server.cfg"
INFO_PATH = "server.info"

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

try:
	Logging.header("fl0w server started on '%s:%d'" % (config.server_address[0], config.server_address[1]))
	server.run(Handler, 
		{"broadcast" : broadcast,
		"routes" : {"info" : Info(), "wallaby_control" : WallabyControl(), "set_type" : SetType(), "get_info" : GetInfo(),
		"w_sync" : SyncServer(config.binary_path, Handler.Channels.WALLABY, deleted_db_path="deleted-w.db"),
		"s_sync" : SyncServer(config.source_path, Handler.Channels.SUBLIME, deleted_db_path="deleted-s.db")}})
except KeyboardInterrupt:
	Logging.header("Gracefully shutting down server.")
	server.stop()
	Logging.success("Server shutdown successful.")
