import Logging
import Routing

from .AsyncServer import Server
from .Broadcast import Broadcast

from time import strftime

class Info(Routing.ServerRoute):
	def setup(self):
		self.start_time = strftime("%H:%M:%S")

	def run(self, data, handler):
		handler.sock.send("Start time: %s\nConnected ST clients: %d\nConnected Wallabies: %d\nAvaliable routes: %s" % (
			self.start_time, len(handler.broadcast.channels[Handler.Channels.SUBLIME]),
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
					if data[address_pair] in ("stop", "restart", "disconnect", "reboot"):
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

	def setup(self, routes, broadcast):
		Logging.info("Handler for '%s:%d' initalised." % (self.sock.address, self.sock.port))
		self.routes = Routing.create_routes(routes)
		self.broadcast = broadcast
		self.channel = None

		
	def handle(self, data, route):
		if route in self.routes:
			self.routes[route].run(data, self)
		else:
			self.sock.send("Invalid route '%s'" % route, "error_report")


	def finish(self):
		if self.channel != None:
			self.broadcast.remove(self.sock, self.channel)
		Logging.info("'%s:%d' disconnected." % (self.sock.address, self.sock.port))


server = Server(("172.20.10.3", 3077), debug=True)

broadcast = Broadcast()
# Populating broadcast channels with all channels defined in Handler.Channels
for channel in Handler.Channels.__dict__:
	if not channel.startswith("_"):
		broadcast.add_channel(Handler.Channels.__dict__[channel])

try:
	Logging.header("fl0w server started.")
	server.run(Handler, 
		{"broadcast" : broadcast, 
		"routes" : {"info" : Info(), "wallaby_control" : WallabyControl(), "set_type" : SetType()}})
except KeyboardInterrupt:
	server.stop()
	Logging.warning("Gracefully shutting down server.")
