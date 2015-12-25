import Logging
import DataTypes

from .AsyncServer import Server
from .Broadcast import Broadcast

class Command:
	def __init__(self):
		self.setup()

	def setup(self):
		pass

	def run(self, data, handler):
		pass


class Info(Command):
	def run(self, data, handler):
		handler.sock.send("Currently connected: %d" % len(handler.broadcast.socks))





class SublimeHandler(Server.Handler):
	def setup(self):
		Logging.info("Handler for '%s' initalised." % self.info[0])
		self.commands = self.kwargs.pop("commands")
		self.broadcast = self.kwargs.pop("broadcast")
		self.broadcast.add(self.sock)
		self.current_prefix = None

		

	def handle(self, data):
		if type(data) == dict:
			data_keys = list(data.keys())
			if len(data_keys) == 1:
				if data_keys[0] in self.commands:
					self.current_prefix = data_keys[0]
					self.commands[self.current_prefix].run(data[data_keys[0]], self)
			else:
				if self.current_prefix != None:
					self.commands[self.current_prefix].run(data, self)				
		else:
			if self.current_prefix != None:
				self.commands[self.current_prefix].run(data, self)


	def finish(self):
		self.broadcast.remove(self.sock)
		Logging.info("%s disconnected." % self.info[0])




server = Server(("127.0.0.1", 3077), SublimeHandler, 
	{"commands" : {"info" : Info()}, "broadcast" : Broadcast()})