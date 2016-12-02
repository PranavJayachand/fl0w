from Highway import Route, Pipe, Client
import Logging
import Config
from Utils import is_wallaby, set_hostname, get_hostname


import socket
import time
import os
import sys
import subprocess
import _thread

CHANNEL = 2
IS_WALLABY = is_wallaby()
PATH = "/home/root/Documents/KISS/bin/" if IS_WALLABY else (sys.argv[1] if len(sys.argv) > 1 else None)

if not PATH:
	Logging.error("No path specified. (Necessary on simulated Wallaby controllers.)")
	exit(1)

if not IS_WALLABY:
	Logging.warning("Binaries that were created for Wallaby Controllers will not run on a simulated Wallaby.")


class WallabyControl(Route):
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



class Subscribe(Route):
	def start(self, handler):
		handler.send({"name" : get_hostname(), "channel" : CHANNEL}, "subscribe")


class Hostname(Pipe):
	def run(self, data, peer, handler):
		if type(data) is dict:
			if "set" in data:
				set_hostname(str(data["set"]))



class Handler(Client):
	def setup(self, routes, debug=False):
		super().setup(routes, piping=True, debug=debug)




CONFIG_PATH = "wallaby.cfg"

config = Config.Config()
config.add(Config.Option("server_address", "ws://127.0.0.1:3077"))
config.add(Config.Option("debug", False, validator=lambda x: True if True or False else False))
config.add(Config.Option("output_unbuffer", "stdbuf"))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	config = config.read_from_file(CONFIG_PATH)


try:
	ws = Handler(config.server_address)
	# setup has to be called before the connection is established
	ws.setup({"subscribe" : Subscribe(), "hostname" : Hostname()}, 
		debug=config.debug)
	ws.connect()
	ws.run_forever()
except KeyboardInterrupt:
	ws.close()