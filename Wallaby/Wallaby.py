from ESock import ESock
from Sync import SyncClient
from Utils import is_socket_related_error
from Utils import capture_trace
import Routing
import Logging

import socket
import time
import os
import sys
import platform

CHANNEL = "w"
IS_WALLABY = True if "ARMv7" in platform.uname().version.lower() else False
PATH = "/home/root/Documents/KISS/" if IS_WALLABY else sys.argv[1]

class WallabyControl(Routing.ClientRoute):
	def __init__(self):
		self.actions_with_params = {"run" : self.run_program}
		self.actions_without_params = {"restart" : self.restart, "disconnect" : self.disconnect, 
		"reboot" : self.reboot, "shutdown" : self.shutdown, "stop" : self.stop}

	def run(self, data, handler):
		if type(data) is str:
			if data in self.actions_without_params.keys():
				self.actions_without_params[data](handler)
		elif type(data[address_pair]) is dict:
			if action in self.actions_with_params.keys():
				self.actions_without_params[action](handler, data[action])


	def stop(self, handler):
		Logging.info("Stopping all processes with executable named botball_user_program.")
		os.system("killall -s 2 botball_user_program")


	def run_program(self, handler, program):
		# WIP: Subprocess with unbuffered stdout required for output streaming
		print(handler)
		print(program)
		os.system("./%s%s" % (handler.sync.folder, program))


	def restart(self, handler):
		Logging.warning("Restart not implemented yet.")
		

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
				if not is_socket_related_error(e):
					capture_trace()
				break


	def stop(self):
		self.sock.close()

wallaby_client = WallabyClient(("127.0.0.1", 3077), debug=True)
try:
	wallaby_client.start()
except KeyboardInterrupt:
	wallaby_client.stop()
