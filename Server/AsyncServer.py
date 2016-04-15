from ESock import ESock
import DataTypes
import Logging

import sys
from Utils import capture_trace
from Utils import is_socket_related_error
import socket
import _thread



class Server:
	def __init__(self, host_port_pair, debug=False, compression_level=None):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.sock.bind(host_port_pair)
		except OSError as e:
			Logging.error(str(e))
			exit(1)
		self.sock.listen(2)
		self.handlers = []
		self.debug = debug
		self.compression_level = compression_level


	def run(self, handler, handler_args={}):
		self.handler = handler
		while 1:
			sock, info = self.sock.accept()
			if self.compression_level:
				sock = ESock(sock, debug=self.debug, compression_level=self.compression_level)
			else:
				sock = ESock(sock, debug=self.debug)

			handler = self.handler(sock, info, **handler_args)
			self.handlers.append(handler)
			_thread.start_new_thread(self.controller, (handler, ))


	def stop(self):
		for handler in self.handlers:
			self.attempt_graceful_close(handler, handler.sock)


	def controller(self, handler):
		while 1:
			try:
				data, route = handler.sock.recv()
				handler.handle(data, route)
			except Exception as e:
				if not is_socket_related_error(e):
					self.print_trace(handler.sock)
				self.attempt_graceful_close(handler, handler.sock)
				_thread.exit()


	def print_trace(self, sock):
		Logging.error("An unhandled exception forced the controller for '%s:%d' to terminate." % (sock.address, sock.port))
		capture_trace()


	def attempt_graceful_close(self, handler, sock):
		try:
			handler.finish()
		except Exception:
			self.print_trace(sock)
		finally:
			if handler in self.handlers:
				del self.handlers[self.handlers.index(handler)]
			handler.sock.close()


	class Handler:
		def __init__(self, sock, info, **kwargs):
			self.sock = sock
			self.info = info
			self.setup(**kwargs)

		def setup(self, **kwargs):
			pass

		def handle(self, data):
			pass

		def finish(self):
			pass
