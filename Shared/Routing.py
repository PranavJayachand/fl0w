import ESock

BROADCAST = 0
ROUTE = 1
SOCK = 2


class InvalidRouteSetup(AttributeError):
	def __init__(self, msg):
		super(AttributeError, self).__init__(msg)


class InvalidRouteLength(AttributeError):
	def __init__(self, msg):
		super(AttributeError, self).__init__(msg)


class ServerRoute:
	REQUIRED = []
	PATCHED = False

	def __init__(self, **kwargs):
		pass

	def run(self, data, handler):
		pass

	def start(self, handler):
		pass


class ClientRoute:
	def run(self, data, handler):
		pass


def create_routes(routes, handler):
	routes = routes.copy()
	reverse_routes = {}
	for prefix in routes:
		if len(prefix) > ESock.MAX_ROUTE_LENGTH:
			raise InvalidRouteLength("'%s' is too long (maximum: %d)" % (prefix, ESock.MAX_ROUTE_LENGTH))
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
		routes[prefix].start(handler)
	return routes