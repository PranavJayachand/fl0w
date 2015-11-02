import Logging
import DataTypes

from .AsyncServer import Server
from .Broadcast import Broadcast

class Command:
	def __init__(self, prefix, auth_required=True):
		self.prefix = prefix
		self.auth_required = auth_required

	def run(self, handler):
		pass

	def __eq__(self, other):
		return self.prefix == other.prefix


class Info(Command):
	def __init__(self):
		super().__init__("info", auth_required=False)

	def run(self, handler):
		return ["Link Clients connected: %d | Sublime Clients connected: %d" % 
			(len(handler.link_broadcast), len(handler.sublime_broadcast)]



class fl0wHandler(Server.Handler):
	def setup(self):
		Logging.info("Handler for '%s' initalised." % self.info[0])
		self.users = self.kwargs.pop("users")
		self.commands = self.kwargs.pop("commands")
		self.sublime_broadcast = self.kwargs.pop("sublime_broadcast")
		self.link_broadcast = self.kwargs.pop("link_broadcast")
		self.client_type = None
		self.authed = False
		

	def handle(self, data, type):
		if self.client_type == None:
			temp = self.sock.recv()
			if 


	def finish(self):
		Logging.info("%s disconnected." % self.info[0])


	def auth(self, collection):
		if "auth" in collection:
			if "user" and "pw" in collection["auth"]:
				temp_user = User(collection["auth"]["user"], collection["auth"]["pw"])
				if temp_user in self.users:
					self.sock.send({"auth" : 1})
					self.authed = True
					return
		self.sock.send({"auth" : 0})
		self.sock.close()


class User:
	def __init__(self, username, password):
		self.username = username
		self.password = password

	def __eq__(self, other):
		if self.username == other.username and self.password == other.password:
			return True
		return False

	def __repr__(self):
		return self.username


server = Server(("127.0.0.1", 3077), fl0wHandler, 
	{"users" : [User("test", "123")], "commands" : [Info()], 
	"sublime_broadcast" : Broadcast(), "link_broadcast" : Broadcast()})