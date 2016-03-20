from ESock import ESock
import DataTypes
import Logging

import sys
from Utils import capture_trace
import socket
import _thread



class Server:
	def __init__(self, host_port_pair, debug=False):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind(host_port_pair)
		self.sock.listen(2)
		self.socks = []
		self.debug = debug


	def run(self, handler, handler_args={}):
		self.handler = handler
		while 1:
			sock, info = self.sock.accept()
			self.socks.append(sock)
			_thread.start_new_thread(self.controller, (sock, info, handler_args))


	def stop(self):
		for sock in self.socks:
			try:
				sock.close()
			except (socket.error, OSError):
				pass
		self.sock.close()

	def controller(self, sock, info, handler_args):
		sock = ESock(sock) if not self.debug else ESock(sock, debug=self.debug)
		handler = self.handler(sock, info, **handler_args)
		while 1:
			try:
				data, route = sock.recv()
				handler.handle(data, route)
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				socket_related_error = True
				if type(e) not in (BrokenPipeError, ConnectionResetError, OSError):
					socket_related_error = False
				if type(e) is OSError:
					if str(e) not in ("Connection closed", "[Errno 9] Bad file descriptor"):
						socket_related_error = False
				if not socket_related_error:
					self.print_trace(handler, sock)
				self.attempt_graceful_close(handler, sock)
				_thread.exit()
			except Exception:
				self.print_trace(handler, sock)
				self.attempt_graceful_close(handler, sock)
				_thread.exit()


	def print_trace(self, handler, sock):
		Logging.error("An unhandled exception forced the controller for '%s:%d' to terminate." % (sock.address, sock.port))
		capture_trace()


	def attempt_graceful_close(self, handler, sock):
		try:
			handler.finish()
		except Exception:
			self.print_trace(handler, sock)
		finally:		
			if sock in self.socks:
				del self.socks[self.socks.index(sock)]
			sock.close()
	

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