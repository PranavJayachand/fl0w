from socket import *
from random import getrandbits
from time import time
from time import sleep
import Utils
import Logging
from _thread import start_new_thread

HEY = "HEY".encode()
IDENT_SEED_LENGTH = 64
WHAT = "WHAT".encode()


class MissingInterfaceError(TypeError):
	def __init__(self):
		super(TypeError, self).__init__("platform requires interface parameter.")	


class Disc0very:
	def __init__(self, port, interface="eth0", max_peers=32):
		self.port = port
		self.ident = getrandbits(max_peers * 2)
		self.sock = socket(AF_INET, SOCK_DGRAM)
		self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		self.sock.bind(("", self.port))
		self.discovering = False
		self.enlisting = False
		



	def discover(self, time_out=2):
		if not self.enlisting:
			self.discovering = True
			self.sock.setblocking(False)
			self.sock.sendto(HEY, ('255.255.255.255', self.port))
			end_time = time() + time_out
			servers = []
			while time() < end_time:
				try:
					data = self.sock.recv(512)
					if data != HEY:
						servers.append(data)
				except BlockingIOError:
					sleep(0.2)
			self.discovering = False
			if len(servers) == 0:
				return None
			elif len(servers) > 1:
				self.sock.sendto(WHAT, ('255.255.255.255', self.port))
			else:
				return servers[0]
		

	def enlist(self, interface, blocking=False):
		if not self.discovering:
			if blocking:
				self.__enlist(interface)
			else:
				start_new_thread(self.__enlist, (interface, ))


	# Interface should always be provided when using a Wallaby
	# because wlan0 and wlan1 have an IP address assigned
	def __enlist(self, interface=None):
		self.enlisting = True
		self.sock.setblocking(True)
		ip_address = Utils.get_ip_address(interface)
		data = ""
		while True:
			try:
				data = self.sock.recv(512)
			except BlockingIOError:
				sleep(0.1)
			if data == HEY:
				self.sock.sendto(ip_address.encode(), ('255.255.255.255', self.port))
			elif data == WHAT:
				Logging.error("Apparently more than one server is running. "
					"Investigating...")
			 	# Discover and if other server is found shutdown


def start():
	print("starting")


if __name__ == "__main__":
	from time import sleep
	disc0very = Disc0very(3077)
	server = disc0very.discover()
	if not server:
		print("enlisted")
		disc0very.enlist(None, blocking=True)
	else:
		print(server)