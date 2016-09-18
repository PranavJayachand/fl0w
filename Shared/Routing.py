BROADCAST = 0
ROUTE = 1
SOCK = 2


class InvalidRouteSetup(AttributeError):
	def __init__(self, msg):
		super(AttributeError, self).__init__(msg)


class InvalidRouteLength(AttributeError):
	def __init__(self, msg):
		super(AttributeError, self).__init__(msg)


class Route:
	def run(self, data, handler):
		pass

	def start(self, handler):
		pass


class ServerRoute(Route):
	REQUIRED = []
	PATCHED = False


class ClientRoute(Route):
	pass


def create_routes(routes, handler):
	routes = routes.copy()
	reverse_routes = {}
	for prefix in routes:
		if type(routes[prefix]) is tuple or type(routes[prefix]) is list:
			routes[prefix] = routes[prefix][0](**routes[prefix][1])
		reverse_routes[routes[prefix]] = prefix
	for prefix in routes:
		attrs = dir(routes[prefix])
		if not routes[prefix].PATCHED:
			for required in routes[prefix].REQUIRED:
				if required == BROADCAST:
					routes[prefix].broadcast = handler.broadcast
				elif required == ROUTE:
					routes[prefix].route = reverse_routes[routes[prefix]]
			routes[prefix].PATCHED = True
	return routes


def launch_routes(created_routes, handler):
	for prefix in created_routes:
		created_routes[prefix].start(handler)


def create_exchange_map(routes):
	exchange_map = {-1 : "meta"}
	exchange_id = 0
	for route in routes:
		exchange_map[exchange_id] = route
		exchange_id += 1
	return exchange_map


def validate_exchange_map(routes):
	for key in routes:
		if not type(key) is int and type(routes[key]) is str:
			return False
	return True