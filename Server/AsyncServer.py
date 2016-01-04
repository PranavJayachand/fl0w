from ESock import ESock
import DataTypes

import socket
import _thread


class Server:
	def __init__(self, host_port_pair):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind(host_port_pair)
		self.sock.listen(2)


	def run(self, handler, handler_args=[]):
		self.handler = handler
		while 1:
			sock, info = self.sock.accept()
			_thread.start_new_thread(self.controller, (sock, info, handler_args))


	def stop(self):
		self.sock.close()

	def controller(self, sock, info, handler_args):
		sock = ESock(sock)
		handler = self.handler(sock, info, **handler_args)
		while 1:
			try:
				handler.handle(*sock.recv())
			except (socket.error, OSError):
				handler.finish()
				handler.sock.close()
				_thread.exit()


	class Handler:
		def __init__(self, sock, info, **kwargs):
			self.sock = sock
			self.info = info
			self.kwargs = kwargs
			self.setup()

		def setup(self):
			pass

		def handle(self, data):
			pass

		def finish(self):
			pass