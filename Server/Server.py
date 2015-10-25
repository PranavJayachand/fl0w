import Logging
import DataTypes

from .AsyncServer import Server

class vHandler(Server.Handler):
	def setup(self):
		Logging.info("Handler for '%s' initalised." % self.info[0])
		self.authed = False
		self.users = self.kwargs.pop("users")

	def handle(self, data, type):
		if not self.authed:
			if type == DataTypes.json:
				self.auth(data)


	def finish(self):
		Logging.info("%s disconnected." % self.info[0])


	def auth(self, collection):
		if "auth" in collection:
			if "user" and "pw" in collection["auth"]:
				temp_user = User(collection["auth"]["user"], collection["auth"]["pw"])
				if temp_user in self.users:
					self.sock.send({"auth" : "success"})
					self.authed = True
					return
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


server = Server("127.0.0.1", 1337, vHandler, {"users" : [User("test", "123")]})