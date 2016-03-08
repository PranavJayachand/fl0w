from ESock import ESock
import DataTypes
import Logging

import sys
import traceback
import socket
import _thread

def capture_trace():
	exc_type, exc_value, exc_traceback = sys.exc_info()
	traceback.print_exception(exc_type, exc_value, exc_traceback)

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
		sock = ESock(sock) if not self.debug else ESock(sock, debug=True)
		handler = self.handler(sock, info, **handler_args)
		while 1:
			try:
				data, route = sock.recv()
				handler.handle(data, route)
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				if type(e) is OSError:
					if str(e) not in ("Connection closed", "Bad file descriptor"):
						raise
				handler.finish()
				if sock in self.socks:
					del self.socks[self.socks.index(sock)]
				sock.close()
				_thread.exit()
			except Exception:
				Logging.error("An unhandled exception forced the controller for '%s:%d' to terminate." % (sock.address, sock.port))
				capture_trace()
				try:
					handler.finish()
				except Exception:
					capture_trace()
				if sock in self.socks:
					del self.socks[self.socks.index(sock)]
				sock.close()
				_thread.exit()


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