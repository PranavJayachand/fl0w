from socket import *
from random import getrandbits
from random import choice
from time import time
from time import sleep
import Utils
import Logging
from _thread import start_new_thread


HEY = "HEY".encode()
NAY = "NAY".encode()
WHAT = "WHAT".encode()


class MissingInterfaceError(TypeError):
	def __init__(self):
		super(TypeError, self).__init__("platform requires interface parameter.")	


class Disc0very:
	def __init__(self, port, interface=None, max_peers=32):
		self.port = port
		self.sock = socket(AF_INET, SOCK_DGRAM)
		self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		self.sock.bind(("", self.port))
		self.ip_address = Utils.get_ip_address(interface)
		self.discovering = False
		self.enlisting = False
		


	# Not thread-safe if ran in parallel with __enlist
	def discover(self, time_out=1):
		self.sock.setblocking(False)
		end_time = time() + time_out
		servers = []
		self.sock.sendto(HEY, ('255.255.255.255', self.port))
		while time() < end_time:
			try:
				data, address = self.sock.recvfrom(512)
				address = address[0]
				# If enlisted peer responds with ip address
				if data not in (HEY, NAY) and address != self.ip_address and not data in servers:
					servers.append(data)
				# If another peer is currently discovering
				elif data == HEY and address != self.ip_address:
					self.sock.sendto(NAY, ('255.255.255.255', self.port))
					return self.discover(time_out=time_out)
				# If another peer gave up
				elif data == NAY and address != self.ip_address:
					return None
			except BlockingIOError:
				sleep((choice(range(1, 10)) / 2) / 10)
		if len(servers) == 0:
			return None
		elif len(servers) > 1:
			self.sock.sendto(WHAT, ('255.255.255.255', self.port))
		else:
			return servers[0]
		

	def enlist(self, interface, blocking=False):
		if blocking:
			self.__enlist(interface)
		else:
			start_new_thread(self.__enlist, (interface, ))


	# Not thread-safe if ran in parallel with discover
	# Interface should always be provided when using a Wallaby
	# because wlan0 and wlan1 have an IP address assigned
	def __enlist(self, interface=None):
		self.sock.setblocking(True)
		data = ""
		while True:
			try:
				data, address = self.sock.recvfrom(512)
			except BlockingIOError:
				sleep(0.1)
			if data == HEY:
				self.sock.sendto(self.ip_address.encode(), ('255.255.255.255', self.port))
			elif data == WHAT:
				Logging.error("Apparently more than one server is running. "
					"Investigating...")
			 	# Discover and if other server is found shutdown


if __name__ == "__main__":
	disc0very = Disc0very(3077)
	server = disc0very.discover()
	if not server:
		print("enlisting")
		disc0very.enlist(None, blocking=True)
	else:
		print(server)