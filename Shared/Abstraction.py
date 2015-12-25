import socket
from ESock import ESock

class fl0wAPI:
	def __init__(self, address, client_type):
		self.sock = socket.create_connection(address)

