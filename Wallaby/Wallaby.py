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
import _thread

CHANNEL = "w"
IS_WALLABY = is_wallaby()
PATH = "/home/root/Documents/KISS/bin/" if IS_WALLABY else sys.argv[1]

if not IS_WALLABY:
	Logging.warning("Binaries that were created for Wallaby Controllers will not run on a simulated Wallaby.")

class WallabyControl(Routing.ClientRoute):
	def __init__(self, output_unbuffer):
		self.output_unbuffer = output_unbuffer
		self.actions_with_params = {"run" : self.run_program}
		self.actions_without_params = {"disconnect" : self.disconnect, 
		"reboot" : self.reboot, "shutdown" : self.shutdown, "stop" : self.stop}
		self.currently_running_program = None

	def run(self, data, handler):
		if type(data) is str:
			if data in self.actions_without_params.keys():
				self.actions_without_params[data](handler)
		elif type(data) is dict:
			for action in data:
				if action in self.actions_with_params.keys():
					_thread.start_new_thread(self.actions_with_params[action], (handler, data[action]))


	def run_program(self, handler, program):
		command = [self.output_unbuffer, "-i0", "-o0", "-e0"]
		command.append("%s%s/botball_user_program" % (handler.sync.folder, program))
		self.currently_running_program = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		# Poll process for new output until finished
		for line in iter(self.currently_running_program.stdout.readline, b""):
			handler.sock.send(line.decode(), "std_stream")

		self.currently_running_program.wait()
		handler.sock.send({"return_code" : self.currently_running_program.returncode}, "std_stream")
		self.currently_running_program = None


	def stop(self, handler):
		if self.currently_running_program != None:
			Logging.info("Killing currently running programm.")
			self.currently_running_program.kill()
		else:
			Logging.info("No program started by fl0w.")
		

	def reboot(self, handler):
		self.disconnect(handler)
		os.system("reboot")
		exit(0)

	def shutdown(self, handler):
		self.disconnect(handler)
		os.system("shutdown -h 0")

	def disconnect(self, handler):
		self.stop(handler)
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
	def __init__(self, host_port_pair, routes, debug=False):
		self.sock = ESock(socket.create_connection(host_port_pair), debug=debug)
		self.connected = True
		self.debug = debug
		self.sync = SyncClient(self.sock, PATH, "w_sync", debug=True)
		routes.update({"w_sync" : self.sync})
		self.routes = routes


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
config.add(Config.Option("server_address", ("127.0.0.1", 3077)))
config.add(Config.Option("debug", True, validator=lambda x: True if True or False else False))
config.add(Config.Option("output_unbuffer", "stdbuf"))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	Logging.info("Config file created. Please modify to reflect your setup.")
	exit(1)
	config = config.read_from_file(CONFIG_PATH)

wallaby_client = WallabyClient(config.server_address, 
	{"wallaby_control" : WallabyControl(config.output_unbuffer), "get_info" : GetInfo()},
	debug=config.debug)
try:
	wallaby_client.start()
except KeyboardInterrupt:
	wallaby_client.stop()
