import Logging
import gzip
import Routing
import struct
import json
from Utils import capture_trace
from threading import Lock

from ws4py.websocket import WebSocket
from ws4py.client.threadedclient import WebSocketClient

INDEXED_DICT = 5
NoneType = None.__class__

DATA_TYPES = {str : 0, dict : 1,
	list : 1, bytes : 2,
	int : 3, float : 4, INDEXED_DICT : 5,
	NoneType : 6}


def reverse_dict(dict):
	return {v : k for k, v in dict.items()}


REVERSE_DATA_TYPES = reverse_dict(DATA_TYPES)

INVALID_ROUTE = 1
INVALID_METADATA_LAYOUT = 2
INVALID_DATA_TYPE = 3

META_ROUTE = "meta"

COMPRESSION_LEVEL = 3




class ConvertFailedError(ValueError):
	def __init__(self):
		super(ValueError, self).__init__("conversion failed (invalid data type supplied)")


class Metadata:
	def __init__(self, data_type, m_route):
		self.data_type = REVERSE_DATA_TYPES[data_type]
		self.m_route = m_route


class Meta:
	def run(self, data, handler):
		if type(data) is dict:
			handler.peer_exchange_routes = data
			Logging.info("Received peer exchange routes: %s" % str(data))
			handler.peer_reverse_exchange_routes = reverse_dict(handler.peer_exchange_routes)
			if issubclass(handler.__class__, Client):
				handler.send(handler.exchange_routes, META_ROUTE, indexed_dict=True)
			Routing.launch_routes(handler.routes, handler)
			try:
				handler.ready()
			except AttributeError:
				Logging.warning("Consider to add a ready method to your handler. "
					"Without one, it's pretty much useless.")



def create_metadata(data_type, converted_route, indexed_dict=False):
	return struct.pack("bh",
		DATA_TYPES[data_type] if not indexed_dict else DATA_TYPES[INDEXED_DICT],
		converted_route)


def prepare_data(data):
	original_data_type = type(data)
	if original_data_type in DATA_TYPES:
		data_type = DATA_TYPES[original_data_type]
	else:
		data_type = DATA_TYPES[bytes]
	if original_data_type is str:
		data = data.encode()
	elif original_data_type is dict or original_data_type is list:
		data = json.dumps(data, separators=(',',':')).encode()
	elif original_data_type is NoneType:
		data = "".encode()
	return data, original_data_type


def pack_message(data, exchange_route, compression_level,
	debug=False, indexed_dict=False):
	data, original_data_type = prepare_data(data)
	data = gzip.compress(data, compression_level)
	return create_metadata(original_data_type, exchange_route,
		indexed_dict=indexed_dict) + data



def parse_metadata(message):
	metadata = struct.unpack("bh", message[:4])
	return Metadata(metadata[0], metadata[1])


def parse_message(data, data_type):
	data = convert_data(gzip.decompress(data[4:]), data_type)
	return data


def convert_data(data, data_type, debug=False):
	try:
		if data_type == str:
			data = data.decode()
		elif data_type == int:
			data = int(data.decode())
		elif data_type == float:
			data = float(data.decode())
		elif data_type in (dict, list):
			data = json.loads(data.decode())
		elif data_type == INDEXED_DICT:
			data = json.loads(data.decode())
			indexed_data = {}
			for key in data:
				indexed_data[int(key)] = data[key]
			data = indexed_data
		elif data_type == NoneType:
			data = None
	except Exception:
		Logging.error("Data conversion failed.")
		capture_trace()
		return None
	return data


class Shared:
	def setup(self, routes, compression_level=COMPRESSION_LEVEL, debug=False):
		self.routes = routes
		self.routes["meta"] = Meta()
		self.compression_level = compression_level
		self.debug = debug


	def override_methods(self):
		self.opened = self.patched_opened
		self.received_message = self.patched_received_message
		self.raw_send = self.send
		self.send = self.patched_send


	def patched_opened(self):
		self.address, self.port = self.peer_address
		self.routes = Routing.create_routes(self.routes, self)
		self.exchange_routes = Routing.create_exchange_map(self.routes)
		self.reverse_exchange_routes = reverse_dict(self.exchange_routes)
		# Peer routes have not been received yet. As per convention the meta route
		# has to exist and we need it for our first send to succeed (otherwise it
		# would fail during route lookup
		self.peer_exchange_routes = {-1 : META_ROUTE}
		self.peer_reverse_exchange_routes = reverse_dict(self.peer_exchange_routes)
		try:
			self.post_opened()
		except AttributeError:
			pass


	def patched_received_message(self, message):
		message = message.data
		metadata = parse_metadata(message)
		try:
			route = self.exchange_routes[metadata.m_route]
		except KeyError:
			self.send(Handler.INVALID_ROUTE, META_ROUTE)
			Logging.error("Received message with non-existing route '%d' from '%s:%d'" % (
				metadata.m_route, self.address, self.port))
			return
		data = parse_message(message, metadata.data_type)
		if self.debug:
			data_repr = str(data).replace("\n", " ")
			if len(data_repr) > 80:
				data_repr = data_repr[:80] + "..."
			Logging.info("Received '%s' on route '%s': %s (%s:%d)" % (
				type(data).__name__ if not metadata.data_type == INDEXED_DICT else "indexed_dict", 
				route, data_repr, self.address,
				self.port))
		self.routes[route].run(data, self)


	def patched_send(self, data, route, indexed_dict=False):
		self.raw_send(pack_message(data, self.peer_reverse_exchange_routes[route],
			self.compression_level, debug=self.debug,
			indexed_dict=indexed_dict), binary=True)
		if self.debug:
			data_repr = str(data).replace("\n", " ")
			if len(data_repr) > 80:
				data_repr = data_repr[:80] + "..."
			Logging.info("Sent '%s' on route '%s': %s (%s:%d)" % (
				type(data).__name__, route, data_repr, self.address,
				self.port))



class Server(WebSocket, Shared):
	def setup(self, routes, compression_level=COMPRESSION_LEVEL, debug=False):
		super().setup(routes, compression_level, debug=debug)
		self.override_methods()


	def post_opened(self):
		self.send(self.exchange_routes, META_ROUTE, indexed_dict=True)


class Client(WebSocketClient, Shared):
	def setup(self, routes, compression_level=COMPRESSION_LEVEL, debug=False):
		super().setup(routes, compression_level, debug=debug)
		self.override_methods()
