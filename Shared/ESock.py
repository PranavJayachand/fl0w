import json
import socket
import struct
import DataTypes
import Logging

class ConvertFailedError(ValueError):
	def __init__(self):
		super(ConvertFailedError, self).__init__("conversion failed (false data type supplied)")

def convert_data(data, data_type):
	try:
		if data_type == DataTypes.str:
			data = data.decode()
		elif data_type == DataTypes.int:
			data = int(data.decode())
		elif data_type == DataTypes.float:
			data = float(data.decode())
		elif data_type == DataTypes.json:
			data = json.loads(data.decode())
	except Exception:
		raise ConvertFailedError()
	return data

class ESock:
	def __init__(self, sock, debug=False, disconnect_callback=None):
		self._sock = sock
		self.address, self.port = self._sock.getpeername()
		self.debug = debug
		self.disconnect_callback = disconnect_callback

	def __getattr__(self, attr):
		if attr == "recv":
			return self.recv
		elif attr == "send":
			return self.send
		elif attr == "_ESock__dict":
			return self.__eq__
		return getattr(self._sock, attr)


	def recv(self):
		raw_metadata = self._sock.recv(32)
		if raw_metadata == b"":
			self._sock.close()
			raise socket.error("Connection closed")
		try:
			metadata = struct.unpack("cQ16s", raw_metadata)
		except struct.error:
			Logging.error("Invalid metadata layout: '%s:%d'" % (self.address, self.port))
			if self.disconnect_callback != None:
				self.disconnect_callback()
			self._sock.close()
			return None, ""
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
		try:
			data = convert_data(data, data_type)
		except ConvertFailedError:
			Logging.error("Invalid data type: '%s:%d'" % (self.address, self.port))
			if self.disconnect_callback != None:
				self.disconnect_callback()
			self._sock.close()
			return None, ""
		if self.debug:
			Logging.info("Received %d-long '%s' on route '%s': %s (%s:%d)" % (len(data), type(data).__name__, route, str(data).replace("\n", " "), self.address, self.port))
		return data, route


	def send(self, data, route=""):
		length = len(data)
		data_type = type(data)
		if self.debug:
			Logging.info("Sending %d-long '%s' on route '%s': %s (%s:%d)" % (length, data_type.__name__, route, str(data).replace("\n", " "), self.address, self.port))		
		route = route.encode()
		if data_type is str:
			data = data.encode()
			self.sendall(struct.pack("cQ16s", DataTypes.str, len(data), route) + data)
		elif data_type is dict or data_type is list:
			data = json.dumps(data, separators=(',',':')).encode()
			self.sendall(struct.pack("cQ16s", DataTypes.json, len(data), route) + data)
		elif data_type is bytes:
			self.sendall(struct.pack("cQ16s", DataTypes.bin, len(data), route) + data)
		elif data_type is int:
			self.sendall(struct.pack("cQ16s", DataTypes.int, len(data), route) + data)
		elif data_type is float:
			self.sendall(struct.pack("cQ16s", DataTypes.float, len(data), route) + data)
		else:
			self.sendall(struct.pack("cQ16s", DataTypes.other, len(data), route) + data)


	def __eq__(self, other):
		return self is other