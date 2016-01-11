import Logging
import Routing
import VarSync

from .AsyncServer import Server
from .Broadcast import Broadcast

class Info(Routing.ServerRoute):
	def setup(self, **kwargs):
		self.message = kwargs.pop("message")
		self.counter = 0

	def run(self, data, handler):
		self.counter += 1
		handler.sock.send("Currently connected: %d (Command has been called %d times.) (%s)" % 
			(len(handler.broadcast.socks), self.counter, self.message), "info")


class SublimeHandler(Server.Handler):
	def setup(self):
		Logging.info("Handler for '%s:%d' initalised." % (self.info[0], self.info[1]))
		self.routes = Routing.create_routes(self.kwargs.pop("routes"))
		self.broadcast = self.kwargs.pop("broadcast")
		self.broadcast.add(self.sock)

		
	def handle(self, data, route):
		if route in self.routes:
			self.routes[route].run(data, self)


	def finish(self):
		self.broadcast.remove(self.sock)
		Logging.info("'%s:%d' disconnected." % (self.info[0], self.info[1]))


server = Server(("127.0.0.1", 3077), debug=True)
varsync = VarSync.Server()
varsync.links = ["link1", "link2"]
print(varsync.attrs)
try:
	Logging.header("fl0w server started.")
	server.run(SublimeHandler, {"routes" : {"info" : (Info, {"message" : "Test"}), "varsync" : varsync}, "broadcast" : Broadcast()})
except KeyboardInterrupt:
	server.stop()
	Logging.warning("Gracefully shutting down server.")
