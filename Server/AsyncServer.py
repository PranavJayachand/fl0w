from ESock import ESock
import DataTypes

import socket
import _thread


class Server:
	def __init__(self, host, port, handler, handler_args=[]):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind((host, port))
		self.sock.listen(2)
		self.handler = handler
		self.broadcast = Server.Broadcast()
		while 1:
			sock, info = self.sock.accept()
			_thread.start_new_thread(self.controller, (sock, info, handler_args))


	def controller(self, sock, info, handler_args):
		sock = ESock(sock)
		handler = self.handler(sock, info, self.broadcast, **handler_args)
		self.broadcast.add(sock)
		while 1:
			try:
				data, type = handler.sock.recv()
				handler.handle(data, type)
			except (socket.error, OSError):
				self.broadcast.remove(handler.sock)
				handler.finish()
				handler.sock.close()
				_thread.exit()


	class Handler:
		def __init__(self, sock, info, broadcast, **kwargs):
			self.sock = sock
			self.info = info
			self.broadcast = broadcast
			self.kwargs = kwargs
			self.setup()

		def setup(self):
			pass

		def handle(self, data, type):
			pass

		def finish(self):
			pass


	class Broadcast:
		def __init__(self):
			self.socks = []

		def broadcast(self, data, exclude=[]):
			for sock in self.socks:
				if not sock in exclude:
					sock.send(data)

		def remove(self, sock):
			if sock in self.socks:
				del self.socks[self.socks.index(sock)]

		def add(self, sock):
			if not sock in self.socks:
				self.socks.append(sock)