import json
import socket
import struct
import time
import DataTypes

class ESock:
	def __init__(self, sock):
		self._sock = sock

	def __getattr__(self, attr):
		if attr == "recv":
			return self.recv
		elif attr == "send":
			return self.send
		elif attr == "_ESock__dict":
			return self.__eq__
		return getattr(self._sock, attr)


	def recv(self):
		raw_metadata = self._sock.recv(8)
		if raw_metadata == b"":
			self._sock.close()
			raise socket.error("Connection closed")
		metadata = struct.unpack("cI", raw_metadata)
		data_type = metadata[0]
		data_length = metadata[1]
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
		return data

	def send(self, data):
		data_type = type(data)
		if data_type is str:
			data = data.encode()
			self.sendall(struct.pack("cI", DataTypes.str, len(data)) + data)
		elif data_type is dict or data_type is list:
			data = json.dumps(data).encode()
			self.sendall(struct.pack("cI", DataTypes.json, len(data)) + data)
		elif data_type is bytes:
			self.sendall(struct.pack("cI", DataTypes.bin, len(data)) + data)
		else:
			self.sendall(struct.pack("cI", DataTypes.other, len(data)) + data)


	def __eq__(self, other):
		return self.__dict == other.__dict__