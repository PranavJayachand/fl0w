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
			handler.broadcast.add(handler.sock, handler.channel)
		elif data == "w":
			handler.channel = Handler.Channels.WALLABY
			handler.broadcast.add(handler.sock, handler.channel)
		else:
			handler.sock.close()
			return
		Logging.info("'%s:%d' has identified as a %s client." % (handler.info[0], handler.info[1], 
			"Sublime Text" if handler.channel == Handler.Channels.SUBLIME else 
			"Wallaby" if handler.channel == Handler.Channels.WALLABY else 
			"Unknown (will not subscribe to broadcast)"))


class Handler(Server.Handler):
	class Channels:
		SUBLIME = 1
		WALLABY = 2

	def setup(self, routes, broadcast, last_stop):
		Logging.info("Handler for '%s:%d' initalised." % (self.sock.address, self.sock.port))
		self.cached_routes = {}
		self.broadcast = broadcast
		self.last_stop = last_stop
		self.channel = None
		self.routes = Routing.create_routes(routes, self)
		self.start_time = time()

		
	def handle(self, data, route):
		if route in self.routes:
			self.routes[route].run(data, self)
		else:
			self.sock.send("Invalid route '%s'" % route, "error_report")


	def get_route(self, route_instance):
		if route_instance not in self.cached_routes: 
			for route in self.routes:
				if self.routes[route] is route_instance:
					self.cached_routes[route_instance] = route
				return route
			return None
		else:
			return self.cached_routes[route_instance]


	def finish(self):
		if self.channel != None:
			self.broadcast.remove(self.sock, self.channel)
		Logging.info("'%s:%d' disconnected." % (self.sock.address, self.sock.port))



CONFIG_PATH = "server.cfg"
INFO_PATH = "server.info"

config = Config.Config()
config.add(Config.Option("server_address", ("127.0.0.1", 3077)))
config.add(Config.Option("debug", True, validator=lambda x: True if True or False else False))
config.add(Config.Option("binary_path", "Binaries", validator=os.path.isdir))
config.add(Config.Option("source_path", "Source", validator=os.path.isdir))

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
	# Trying to obtain last stop time
	last_stop = 0
	try:
		last_stop = json.loads(open(INFO_PATH, "r").read())["last_stop"]
	except IOError:
		Logging.warning("Unable to obtain last shutdown time. (You can ignore this message if it's your first time starting fl0w)")
	except (ValueError, KeyError):
		Logging.error("%s has been modified an contains invalid information." % CONFIG_PATH)
	Logging.info("Last shutdown time: %d" % last_stop)
	server.run(Handler, 
		{"broadcast" : broadcast, "last_stop" : last_stop,
		"routes" : {"info" : Info(), "wallaby_control" : WallabyControl(), "set_type" : SetType(),
		"w_sync" : SyncServer(config.binary_path, Handler.Channels.WALLABY)}})
except KeyboardInterrupt:
	Logging.header("Gracefully shutting down server.")
	server.stop()
	# Dumping stop time
	open(INFO_PATH, "w").write(json.dumps({"last_stop" : time()}))
	Logging.success("Server shutdown successful.")
