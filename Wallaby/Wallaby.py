import fl0w
from ESock import ESock
import Routing
import socket
import time
import os
import sys


class WallabyControl(Routing.ClientRoute):
	def run(self, data, handler):
		commands = {"stop" : self.stop, "restart" : self.restart, 
		"disconnect" : self.disconnect, "reboot" : self.reboot, 
		"shutdown" : self.shutdown}
		if data in commands:
			commands[data](handler)

	def stop(self, handler):
		print("Stop nyi")

	def restart(self, handler):
		self.disconnect(handler)
		time.sleep(15)
		os.execl(sys.executable, *([sys.executable]+sys.argv))

	def reboot(self, handler):
		os.system("reboot")
		exit(0)

	def shutdown(self, handler):
		os.system("shutdown -h 0")

	def disconnect(self, handler):
		handler.sock.close()




class WallabyClient:
	def __init__(self, host_port_pair, debug=False):
		self.sock = ESock(socket.create_connection(host_port_pair), debug=debug)
		self.connected = True
		self.debug = debug
		self.routes = {"wallaby_control" : WallabyControl()}


	def start(self):
		self.sock.send("w", "set_type")
		while 1 and self.connected:
			try:
				data = self.sock.recv()
				if data[1] in self.routes:
					self.routes[data[1]].run(data[0], self)
			except (OSError, socket.error):
				self.connected = False


	def stop(self):
		self.sock.close()

wallaby_client = WallabyClient(("127.0.0.1", 3077))
try:
	wallaby_client.start()
except KeyboardInterrupt:
	wallaby_client.stop()