from ESock import ESock
from Sync import SyncClient
from Utils import is_socket_related_error
from Utils import capture_trace
from Utils import is_wallaby
import Routing
import Logging
import Config

import socket
import time
import os
import sys
import platform
import subprocess

CHANNEL = "w"
IS_WALLABY = is_wallaby()
PATH = "/home/root/Documents/KISS/bin/" if IS_WALLABY else sys.argv[1]

class WallabyControl(Routing.ClientRoute):
	def __init__(self):
		self.actions_with_params = {"run" : self.run_program}
		self.actions_without_params = {"restart" : self.restart, "disconnect" : self.disconnect, 
		"reboot" : self.reboot, "shutdown" : self.shutdown, "stop" : self.stop}

	def run(self, data, handler):
		if type(data) is str:
			if data in self.actions_without_params.keys():
				self.actions_without_params[data](handler)
		elif type(data) is dict:
			for action in data:
				print(action)
				if action in self.actions_with_params.keys():
					self.actions_with_params[action](handler, data[action])


	def run_program(self, handler, program):
		if not IS_WALLABY:
			command = ["gstdbuf", "-i0", "-o0", "-e0"]
		else:
			command = ["stdbuf", "-i0", "-o0", "-e0"]
		command.append("%s%s/botball_user_program" % (handler.sync.folder, program))
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		# Poll process for new output until finished
		for line in iter(process.stdout.readline, b""):
			handler.sock.send(line.decode(), "std_stream")
			print(line)

		process.wait()
		handler.sock.send({"return_code" : process.returncode}, "std_stream")


	def stop(self, handler):
		Logging.info("Stopping all processes with executable named botball_user_program.")
		os.system("killall -s 2 botball_user_program")


	def restart(self, handler):
		Logging.warning("Restart not implemented yet.")
		

	def reboot(self, handler):
		os.system("reboot")
		exit(0)

	def shutdown(self, handler):
		os.system("shutdown -h 0")

	def disconnect(self, handler):
		handler.sock.close()


def get_wallaby_hostname():
	return open("/etc/hostname", "r").read()

class GetInfo(Routing.ClientRoute):
	def run(self, data, handler):
		if data == "":
			handler.sock.send({"type" : CHANNEL, 
				"name" : platform.node() if not IS_WALLABY else get_wallaby_hostname()}, "get_info")
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
		self.sync = SyncClient(self.sock, PATH, "w_sync", debug=True)
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



CONFIG_PATH = "wallaby.cfg"

config = Config.Config()
config.add(Config.Option("server_address", ("192.168.0.20", 3077)))
config.add(Config.Option("debug", True, validator=lambda x: True if True or False else False))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	Logging.info("Config file created. Please modify to reflect your setup.")
	exit(1)
	config = config.read_from_file(CONFIG_PATH)

wallaby_client = WallabyClient(config.server_address, debug=config.debug)
try:
	wallaby_client.start()
except KeyboardInterrupt:
	wallaby_client.stop()
