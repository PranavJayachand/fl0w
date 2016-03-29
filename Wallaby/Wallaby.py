from ESock import ESock
from Sync import SyncClient
import Routing

import socket
import time
import os
import sys
import platform

CHANNEL = "w"
IS_WALLABY = True if "ARMv7" in platform.uname().version.lower() else False

class WallabyControl(Routing.ClientRoute):
	def __init__(self):
		self.actions_with_params = {"stop" : self.stop, "run" : self.run}
		self.actions_without_params = {"restart" : self.restart, "disconnect" : self.disconnect, 
		"reboot" : self.reboot, "shutdown" : self.shutdown}

	def run(self, data, handler):
		if data in self.actions_without_params.keys():
			self.actions_without_params[action](handler)
		elif type(data[address_pair]) is dict:
			if action in self.actions_with_params.keys():
				self.actions_without_params[action](data[action], handler)

	def stop(self, handler):
		os.system("killall -s 2 botball_user_program")

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


class GetInfo(Routing.ClientRoute):
	def run(self, data, handler):
		if data == "":
			handler.sock.send({"type" : CHANNEL, "name" : platform.node()}, "get_info")
		elif "name" in data:
			if IS_WALLABY:
				open("/etc/hostname", "w").write(str(data["name"]))
			else:
				Logging.info("Hostname change: '%s'" % str(data["name"]))


class WallabyClient:
	def __init__(self, host_port_pair, debug=False):
		self.sock = ESock(socket.create_connection(host_port_pair), debug=debug)
		self.connected = True
		self.debug = debug
		self.sync = SyncClient(self.sock, sys.argv[1], "w_sync", debug=True)
		self.routes = {"wallaby_control" : WallabyControl(), "w_sync" : self.sync, 
		"get_info" : GetInfo()}


	def start(self):
		self.sync.start()
		while 1 and self.connected:
			data = self.sock.recv()
			try:
				if data[1] in self.routes:
				self.routes[data[1]].run(data[0], self)
			except Exception as e:



	def stop(self):
		self.sock.close()

wallaby_client = WallabyClient(("127.0.0.1", 3077), debug=True)
try:
	wallaby_client.start()
except KeyboardInterrupt:
	wallaby_client.stop()
