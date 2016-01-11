import json
import socket
import struct
import DataTypes
import Logging

class ESock:
	def __init__(self, sock, debug=False):
		self._sock = sock
		self.address, self.port = self._sock.getpeername()
		self.debug = debug

	def __getattr__(self, attr):
		if attr == "recv":
			return self.recv
		elif attr == "send":
			return self.send
		elif attr == "_ESock__dict":
			return self.__eq__
		return getattr(self._sock, attr)


	def recv(self):
		raw_metadata = self._sock.recv(24)
		if raw_metadata == b"":
			self._sock.close()
			raise socket.error("Connection closed")
		metadata = struct.unpack("cI16s", raw_metadata)
		data_type = metadata[0]
		data_length = metadata[1]
		route = metadata[2].rstrip(b"\x00").decode()
		data = b''
		bufsize = 4096
		while len(data) < data_length:
			if len(data) + bufsize <= data_length:
				packet = self._sock.recv(bufsize)
			else:
				packet = self._sock.recv(data_length % bufsize)
			if not packet:
				return None
			data += packet
		if data_type == DataTypes.str:
			data = data.decode()
		elif data_type == DataTypes.json:
			data = json.loads(data.decode())
		if self.debug:
			Logging.info("Received %d-long '%s' on route '%s': %s (%s:%d)" % (data_length, type(data).__name__, route, str(data), self.address, self.port))
		return data, route

	def send(self, data, route=""):
		length = len(data)
		data_type = type(data)
		if self.debug:
			Logging.info("Sending %d-long '%s' on route '%s': %s (%s:%d)" % (length, data_type.__name__, route, str(data), self.address, self.port))		
		route = route.encode()
		if data_type is str:
			data = data.encode()
			self.sendall(struct.pack("cI16s", DataTypes.str, len(data), route) + data)
		elif data_type is dict or data_type is list:
			data = json.dumps(data).encode()
			self.sendall(struct.pack("cI16s", DataTypes.json, len(data), route) + data)
		elif data_type is bytes:
			self.sendall(struct.pack("cI16s", DataTypes.bin, len(data), route) + data)
		else:
			self.sendall(struct.pack("cI16s", DataTypes.other, len(data), route) + data)



	def __eq__(self, other):
		return self.__dict == other.__dict__