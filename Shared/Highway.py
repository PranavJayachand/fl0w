import Logging
import gzip
import struct
import json
import binascii
import os

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
META_ROUTE_INDEX = 0

PIPE_ROUTE = "pipe"

PACK_FORMAT = "BH"
METADATA_LENGTH = struct.calcsize(PACK_FORMAT)

# Percise enough for now
PIPE_ID_LENGTH = 8

# Perspective: Packaged by client 1 for server
PIPE_SRC_PACK_FORMAT = "BH%is" % PIPE_ID_LENGTH
PIPE_SRC_METADATA_LENGTH = struct.calcsize(PIPE_SRC_PACK_FORMAT)
PIPE_SRC_METADATA_LENGTH = struct.calcsize(PIPE_SRC_PACK_FORMAT)

# Perspective: Packaged by server for client 2
PIPE_DEST_PACK_FORMAT = "B%is" % PIPE_ID_LENGTH
PIPE_DEST_METADATA_LENGTH = struct.calcsize(PIPE_DEST_PACK_FORMAT)
PIPE_DEST_METADATA_LENGTH = struct.calcsize(PIPE_DEST_PACK_FORMAT)


# Routing related
class Route:
	def run(self, data, handler):
		pass

	def start(self, handler):
		pass

	def stop(self, handler):
		pass


class Pipe(Route):
	def run(self, data, peer, handler):
		pass


def create_routes(routes):
	routes = routes.copy()
	for prefix in routes:
		if type(routes[prefix]) is tuple or type(routes[prefix]) is list:
			routes[prefix] = routes[prefix][0](**routes[prefix][1])
	return routes


def launch_routes(created_routes, handler):
	for prefix in created_routes:
		try:
			created_routes[prefix].start(handler)
		except AttributeError:
			pass


def close_routes(created_routes, handler):
	for prefix in created_routes:
		try:
			created_routes[prefix].stop(handler)
		except AttributeError:
			pass


def create_exchange_map(routes):
	exchange_map = {0 : META_ROUTE}
	exchange_id = 1
	for route in routes:
		if route != META_ROUTE:
			exchange_map[exchange_id] = route
			exchange_id += 1
	return exchange_map


def validate_exchange_map(routes):
	for key in routes:
		if not type(key) is int and type(routes[key]) is str:
			return False
	return True


class ConvertFailedError(ValueError):
	def __init__(self):
		super(ValueError, self).__init__("conversion failed (invalid data type supplied)")


# Built-in routes
class Meta(Route):
	def run(self, data, handler):
		if type(data) is dict:
			handler.peer_exchange_routes = data
			if handler.debug:
				Logging.success("Received peer exchange routes: %s" % str(data))
			handler.peer_reverse_exchange_routes = reverse_dict(handler.peer_exchange_routes)
			if issubclass(handler.__class__, Client):
				handler.send(handler.exchange_routes, META_ROUTE, indexed_dict=True)
			try:
				handler.ready()
			except AttributeError:
				pass
			if handler.debug:
				Logging.info("Launching routes.")
			launch_routes(handler.routes, handler)
			if handler.debug:
				Logging.info("Routes launched.")
		if type(data) is int:
			if data == 1:
				Logging.error("Last route was invalid.")
			elif data == 2:
				Logging.error("Last metadata layout was invalid.")
			elif data == 3:
				Logging.error("Last data type was invalid.")
			else:
				Logging.error("Unknown error code.")


class ServerPipe(Route):
	def start(self, handler):
		if issubclass(handler.__class__, Client):
			Logging.error("Server-exclusive route")
			handler.close()


	def run(self, data, handler):
		data_type, m_route, id_ = parse_pipe_src_metadata(data)
		id_ = id_.decode()
		data = convert_data(data[PIPE_SRC_METADATA_LENGTH:], data_type)
		route = handler.exchange_routes[m_route]
		if id_ in handler.peers:
			if handler.debug:
				Logging.info("Forwarding to '%s' on route '%s'" % (id_, route),
					color=Logging.LIGHT_YELLOW)
			handler.peers[id_].send(pack_pipe_dest_message(data, handler.id_), route)
		else:
			Logging.error("'%s' is not present in peers." % id_)


class DummyPipe(Route):
	def run(self, data, handler):
		pass


# Message packing and unpacking
def create_metadata(data_type, converted_route, indexed_dict=False):
	return struct.pack(PACK_FORMAT,
		DATA_TYPES[data_type] if not indexed_dict else DATA_TYPES[INDEXED_DICT],
		converted_route)


# Perspective: Packaged by client 1 for server
def create_pipe_src_metadata(data_type, converted_route, id_, indexed_dict=False):
	return struct.pack(PIPE_SRC_PACK_FORMAT,
		DATA_TYPES[data_type] if not indexed_dict else DATA_TYPES[INDEXED_DICT],
		converted_route, id_.encode())

# Perspective: Packaged by server for client 2
def create_pipe_dest_metadata(data_type, id_, indexed_dict=False):
	return struct.pack(PIPE_DEST_PACK_FORMAT,
		DATA_TYPES[data_type] if not indexed_dict else DATA_TYPES[INDEXED_DICT],
		id_.encode())


def pack_message(data, exchange_route,
	debug=False, indexed_dict=False):
	data, original_data_type = prepare_data(data)
	return create_metadata(original_data_type, exchange_route,
		indexed_dict=indexed_dict) + data


def pack_pipe_src_message(data, exchange_route, id_, debug=False,
	indexed_dict=False):
	data, original_data_type = prepare_data(data)
	return create_pipe_src_metadata(original_data_type, exchange_route, id_,
		indexed_dict=indexed_dict) + data

def pack_pipe_dest_message(data, id_, debug=False,
	indexed_dict=False):
	data, original_data_type = prepare_data(data)
	return create_pipe_dest_metadata(original_data_type, id_,
		indexed_dict=indexed_dict) + data


def parse_metadata(message):
	metadata = struct.unpack(PACK_FORMAT, message[:METADATA_LENGTH])
	return REVERSE_DATA_TYPES[metadata[0]], metadata[1]


def parse_pipe_src_metadata(message):
	metadata = struct.unpack(PIPE_SRC_PACK_FORMAT, message[:PIPE_SRC_METADATA_LENGTH])
	return REVERSE_DATA_TYPES[metadata[0]], metadata[1], metadata[2]


def parse_pipe_dest_metadata(message):
	metadata = struct.unpack(PIPE_DEST_PACK_FORMAT, message[:PIPE_DEST_METADATA_LENGTH])
	return REVERSE_DATA_TYPES[metadata[0]], metadata[1]

def convert_data(data, data_type, debug=False):
	try:
		if data_type == str:
			try:
				data = data.decode()
			except UnicodeDecodeError:
				Logging.warning("Unicode characters are not properly encoded. "
					"Falling back to unicode_escape.")
				data = data.decode("unicode_escape")
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


def prepare_data(data):
	original_data_type = type(data)
	if original_data_type is str:
		data = data.encode()
	elif original_data_type in (int, float):
		data = str(data).encode()
	elif original_data_type is dict or original_data_type is list:
		data = json.dumps(data, separators=(',',':')).encode()
	elif original_data_type is NoneType:
		data = "".encode()
	return data, original_data_type


class Shared:
	def setup(self, routes, debug=False):
		self.routes = routes
		self.routes[META_ROUTE] = Meta()
		self.routes = create_routes(self.routes)
		self.reverse_routes = reverse_dict(self.routes)
		self.exchange_routes = create_exchange_map(self.routes)
		self.reverse_exchange_routes = reverse_dict(self.exchange_routes)
		# Peer routes have not been received yet. As per convention the meta route
		# has to exist and we need it for our first send to succeed (otherwise it
		# would fail during route lookup).
		self.peer_exchange_routes = {META_ROUTE_INDEX : META_ROUTE}
		self.peer_reverse_exchange_routes = reverse_dict(self.peer_exchange_routes)
		self.debug = debug


	def override_methods(self):
		self.opened = self.patched_opened
		self.received_message = self.patched_received_message
		self.raw_send = self.send
		self.send = self.patched_send


	def patched_opened(self):
		self.address, self.port = self.peer_address
		try:
			self.post_opened()
		except AttributeError:
			pass


	def patched_received_message(self, message):
		message = message.data
		data_type, m_route = parse_metadata(message)
		try:
			route = self.exchange_routes[m_route]
		except KeyError:
			self.send(INVALID_ROUTE, META_ROUTE)
			Logging.error("Received message with non-existing route '%d' from '%s:%d'" % (
				m_route, self.address, self.port))
			return
		data = convert_data(message[METADATA_LENGTH:], data_type)
		if self.debug:
			data_repr = str(data).replace("\n", " ")
			if len(data_repr) > 80:
				data_repr = data_repr[:80] + "..."
			Logging.info("Received '%s' on route '%s': %s (%s:%d)" % (
				type(data).__name__ if not data_type == INDEXED_DICT else "indexed_dict",
				route, data_repr, self.address,
				self.port))
		try:
			route = self.routes[route]
		except:
			Logging.warning("'%s' does not exist." % route)
		else:
			if not issubclass(route.__class__, Pipe):
				route.run(data, self)
			else:
				data_type, peer = parse_pipe_dest_metadata(data)
				peer = peer.decode()
				data = convert_data(data[PIPE_DEST_METADATA_LENGTH:], data_type, debug=self.debug)
				route.run(data, peer, self)


	def patched_send(self, data, route, indexed_dict=False):
		try:
			self.raw_send(pack_message(data,
				self.peer_reverse_exchange_routes[route],
				debug=self.debug, indexed_dict=indexed_dict),
			binary=True)
		except KeyError:
			Logging.error("'%s' is not a valid peer route." % route)
		else:
			if self.debug:
				data_repr = str(data).replace("\n", " ")
				if len(data_repr) > 80:
					data_repr = data_repr[:80] + "..."
				Logging.info("Sent '%s' on route '%s': %s (%s:%d)" % (
					type(data).__name__, route, data_repr, self.address,
					self.port))



class Server(WebSocket, Shared):
	def setup(self, routes, websockets, piping=False, debug=False):
		if piping:
			routes[PIPE_ROUTE] = ServerPipe()
		super().setup(routes, debug=debug)
		self.websockets = websockets
		self._last_websockets = self.websockets.copy()
		self._peers = {}
		id_ = binascii.b2a_hex(os.urandom(PIPE_ID_LENGTH // 2)).decode()
		while id_ in self.peers:
			id_ = binascii.b2a_hex(os.urandom(PIPE_ID_LENGTH // 2)).decode()
		self.id_ = id_
		self.override_methods()


	@property
	def peers(self):
		if self.websockets != self._last_websockets:
			if self.debug:
				Logging.info("Rebuilding peers. (currently connected: %i)" %
					len(self.websockets))
			self._peers = {}
			for websocket in self.websockets:
				self._peers[self.websockets[websocket].id_] = self.websockets[websocket]
			self._last_websockets = self.websockets.copy()
		return self._peers


	def post_opened(self):
		self.send(self.exchange_routes, META_ROUTE, indexed_dict=True)


class Client(WebSocketClient, Shared):
	def setup(self, routes, piping=False, debug=False):
		if piping:
			self.pipe = self.__pipe
			routes[PIPE_ROUTE] = DummyPipe()
		super().setup(routes, debug=debug)

		self.override_methods()

	def __pipe(self, data, route, id_):
		try:
			self.send(pack_pipe_src_message(data,
				self.peer_reverse_exchange_routes[route], id_, debug=self.debug),
				PIPE_ROUTE)
		except KeyError:
			Logging.warning("'%s' does not exist." % route)
