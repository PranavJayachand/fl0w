from Highway import Route, Pipe, Client
import Logging
import Config
import Utils

import socket
import time
import os
import sys
import subprocess
from random import randint
from _thread import start_new_thread
import threading

CHANNEL = 2
IS_WALLABY = Utils.is_wallaby()
PATH = "/home/root/Documents/KISS/bin/" if IS_WALLABY else (sys.argv[1] if len(sys.argv) > 1 else None)

PATH = os.path.abspath(PATH)

if PATH[-1] != "/":
	PATH = PATH + "/"


LIB_WALLABY = "/usr/lib/libwallaby.so"
WALLABY_PROGRAMS = "/root/Documents/KISS/bin/"

if not PATH:
	Logging.error("No path specified. (Necessary on simulated Wallaby controllers.)")
	exit(1)

if not IS_WALLABY:
	Logging.warning("Binaries that were created for Wallaby Controllers will not run on a simulated Wallaby.")


class SensorReadout:
	ANALOG = 1
	DIGITAL = 2
	NAMED_MODES = {ANALOG : "analog", DIGITAL : "digital"}
	MODES = tuple(NAMED_MODES.keys())


	def __init__(self, handler, poll_rate=0.2):
		self.poll_rate = poll_rate
		self.handler = handler
		self.peer_lock = threading.Lock()
		self.peers = {}
		self.readout_required = {SensorReadout.ANALOG : [],
			SensorReadout.DIGITAL : []}
		self.generate_random_values = False
		# Running on actual hardware?
		if IS_WALLABY:
			if not os.path.exists(LIB_WALLABY):
				Logging.error("The Wallaby library should normally exist on "
					"a Wallaby. You broke something, mate.")
				self.generate_random_values = True
		else:
			Logging.warning("Sensor data can not be read on a dev-system. "
				"Generating random values instead.")
			self.generate_random_values = True
		# Generate random values?
		if not self.generate_random_values:
			self.wallaby_library = cdll.LoadLibrary(LIB_WALLABY)
			self.get_sensor_value = self.__get_sensor_value
		else:
			self.get_sensor_value = self.__get_random_value
		start_new_thread(self._sensor_fetcher, ())


	def subscribe(self, port, mode, peer):
		if port not in self.readout_required[mode]:
			self.readout_required[mode].append(port)
		if not peer in self.peers:
			self.peer_lock.acquire()
			self.peers[peer] = {SensorReadout.ANALOG : [],
			SensorReadout.DIGITAL : []}
			self.peer_lock.release()
		self.peers[peer][mode].append(port)


	def unsubscribe(self, port, mode, peer):
		if peer in self.peers:
			if port in self.peers[peer][mode]:
				self.peer_lock.acquire()
				del self.peers[peer][mode][self.peers[peer][mode].index(port)]
				self.peer_lock.release()
				self.determine_required_readouts()


	def determine_required_readouts(self):
		readout_required = {SensorReadout.ANALOG : [],
			SensorReadout.DIGITAL : []}
		self.peer_lock.acquire()
		for peer in self.peers:
			for mode in (SensorReadout.ANALOG, SensorReadout.DIGITAL):
				for port in self.peers[peer][mode]:
					if not port in readout_required[mode]:
						readout_required[mode].append(port)
		self.peer_lock.release()
		self.readout_required = readout_required


	def unsubscribe_all(self, peer):
		if peer in self.peers:
			self.peer_lock.acquire()
			del self.peers[peer]
			self.peer_lock.release()
			self.determine_required_readouts()


	def __get_sensor_value(self, port, mode):
		if mode == SensorReadout.ANALOG:
			return self.wallaby_library.analog(port)
		elif mode == SensorReadout.DIGITAL:
			return self.wallaby_library.digital(port)


	def __get_random_value(self, port, mode):
		if mode == SensorReadout.ANALOG:
			return randint(0, 4095)
		elif mode == SensorReadout.DIGITAL:
			return randint(0, 1)



	def _sensor_fetcher(self):
		while True:
			current_values = {SensorReadout.ANALOG : {},
			SensorReadout.DIGITAL : {}}
			for mode in SensorReadout.MODES:
				for port in self.readout_required[mode]:
					current_values[mode][port] = self.get_sensor_value(port, mode)
			self.peer_lock.acquire()
			for peer in self.peers:
				readouts = 0
				response = {"analog" : {}, "digital" : {}}
				for mode in SensorReadout.NAMED_MODES:
					for port in self.peers[peer][mode]:
						response[SensorReadout.NAMED_MODES[mode]][port] = current_values[mode][port]
						readouts += 1
				if readouts != 0:
					self.handler.pipe(response, "sensor", peer)
			self.peer_lock.release()
			time.sleep(self.poll_rate)

	@staticmethod
	def valid_port(port, mode):
		if mode == SensorReadout.ANALOG:
			return port >= 0 and port <= 5
		elif mode == SensorReadout.DIGITAL:
			return port >= 0 and port <= 9
		return False


class Identify(Pipe):
	def run(self, data, peer, handler):
		Utils.play_sound(config.identify_sound)
		if handler.debug:
			Logging.success("I was identified!")


class ListPrograms(Pipe):
	def run(self, data, peer, handler):
		programs = []
		if os.path.isdir(PATH):
			for program in os.listdir(PATH):
				if "botball_user_program" in os.listdir(PATH + program):
					programs.append(program)
		else:
			Logging.error("Harrogate folder structure does not exist. "
				"You broke something, mate.")
		handler.pipe(programs, handler.reverse_routes[self], peer)


class StopPrograms(Pipe):
	def run(self, data, peer, handler):
		if handler.debug:
			Logging.info("Stopping all botball programs.")
		output = subprocess.call(["killall", "botball_user_program"], 
			stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


class RunProgram(Pipe):
	def __init__(self, output_unbuffer):
		self.command = [output_unbuffer, "-i0", "-o0", "-e0"]


	def run(self, data, peer, handler):
		if type(data) is str:
			if data[-1] != "/":
				data = data + "/"
			path = "%s%s/botball_user_program" % (PATH, data)
			if os.path.isfile(path):
				program = subprocess.Popen(self.command + [path], 
					stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				start_new_thread(self.stream_stdout, (program, peer, handler))
			else:
				if handler.debug:
					Logging.warning("Program '%s' not found." % data[:-1])

	def stream_stdout(self, program, peer, handler):
		# Poll process for new output until finished
		for line in iter(program.stdout.readline, b""):
			handler.pipe(line.decode(), "std_stream", peer)
		program.wait()
		exit_code = program.returncode if type(program.returncode) is int else -1
		handler.pipe({"exit_code" : exit_code}, "std_stream", peer)


class Sensor(Pipe):
	"""
	->
	{"subscribe" : {"analog" : [1, 2, 3], "digital" : [1, 2, 3]}}
	{"unsubscribe" : {"analog" : [1, 2, 3], "digital" : [1, 2, 3]}}
	{"poll_rate" : 10}

	<-
	{"analog" : {1 : 1240}, "digital" : {1 : 0, 2 : 0}}
	"""
	def run(self, data, peer, handler):
		if type(data) is dict:
			if "poll_rate" in data:
				if type(data["poll_rate"]) in (int, float) and data["poll_rate"] >= 0.1:
					self.sensor_readout.poll_rate = data["poll_rate"]
			for event in ("subscribe", "unsubscribe"):
				if event in data:
					for mode in ("analog", "digital"):
						if mode in data[event]:
							for port in data[event][mode]:
								if type(port) is int:
									if mode == "analog":
										mode = SensorReadout.ANALOG
									elif mode == "digital":
										mode = SensorReadout.DIGITAL
									if SensorReadout.valid_port(port, mode):
										if event == "subscribe":
											self.sensor_readout.subscribe(port, mode, peer)
										elif event == "unsubscribe":
											self.sensor_readout.unsubscribe(port, mode, peer)
		elif type(data) is str:
			if data == "unsubscribe":
				self.sensor_readout.unsubscribe_all(peer)


	def start(self, handler):
		self.sensor_readout = SensorReadout(handler)


class Shutdown(Pipe):
	def run(self, data, peer, handler):
		try:
			subprocess.check_output(["shutdown", "now"])
		except subprocess.CalledProcessError:
			Logging.warning("Shutdown could not be initiated.")


class Reboot(Pipe):
	def run(self, data, peer, handler):
		try:
			subprocess.check_output(["reboot"])
		except subprocess.CalledProcessError:
			Logging.warning("Reboot could not be initiated.")


class Subscribe(Route):
	def start(self, handler):
		handler.send({"name" : Utils.get_hostname(), "channel" : CHANNEL}, "subscribe")


class WhoAmI(Route):
	def run(self, data, handler):
		Logging.header("ID: '%s' - Running as '%s'" % (data["id"], data["user"]))

	def start(self, handler):
		handler.send(None, "whoami")


class Hostname(Pipe):
	def run(self, data, peer, handler):
		if type(data) is dict:
			if "set" in data:
				try:
					Utils.set_hostname(str(data["set"]))
				except Utils.HostnameNotChangedError:
					if IS_WALLABY:
						Logging.error("Hostname change unsuccessful. "
							"Something is wrong with your Wallaby.")
					else:
						Logging.warning("Hostname change unsuccessful. "
							"This seems to be a dev-system, so don't worry too "
							"much about it.")


class Processes(Pipe):
	def run(self, data, peer, handler):
		handler.pipe(
			subprocess.check_output(["ps", "aux"]).decode().split("\n")[1:-1],
			"processes", peer)


class Handler(Client):
	def setup(self, routes, debug=False):
		super().setup(routes, debug=debug)

	def peer_unavaliable(self, peer):
		if self.debug:
			Logging.info("Unsubscribing '%s' from all sensor updates." % peer)
		self.routes["sensor"].sensor_readout.unsubscribe_all(peer)


CONFIG_PATH = "wallaby.cfg"

config = Config.Config()
config.add(Config.Option("server_address", "ws://127.0.0.1:3077"))
config.add(Config.Option("debug", False, validator=lambda x: True if True or False else False))
config.add(Config.Option("output_unbuffer", "stdbuf"))
config.add(Config.Option("identify_sound", "Wallaby/identify.wav",
	validator=lambda x: os.path.isfile(x)))

try:
	config = config.read_from_file(CONFIG_PATH)
except FileNotFoundError:
	config.write_to_file(CONFIG_PATH)
	config = config.read_from_file(CONFIG_PATH)


try:
	ws = Handler(config.server_address)
	# setup has to be called before the connection is established
	ws.setup({"subscribe" : Subscribe(), "hostname" : Hostname(),
		"processes" : Processes(), "sensor" : Sensor(),
		"identify" : Identify(), "list_programs" : ListPrograms(), 
		"whoami" : WhoAmI(), "run_program" : RunProgram(config.output_unbuffer),
		"stop_programs" : StopPrograms(), "shutdown" : Shutdown(),
		"reboot" : Reboot()},
		debug=config.debug)
	ws.connect()
	ws.run_forever()
except KeyboardInterrupt:
	ws.close()