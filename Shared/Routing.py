BROADCAST = 0
ROUTE = 1
LAST_STOP = 2

class InvalidRouteSetup(AttributeError):
	def __init__(self, msg):
		super(AttributeError, self).__init__(msg)

class ServerRoute:
	def __init__(self, **kwargs):
		self.setup(**kwargs)

	def setup(self, **kwargs):
		pass

	def run(self, data, handler):
		pass

class ClientRoute:
	def run(self, data, handler):
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
		if "REQUIRED" in attrs:
			if not "start" in attrs:
				raise InvalidRouteSetup("method named 'start' required if 'REQUIRE' is defined")
			for required in type(routes[prefix]).REQUIRED:
				if required == BROADCAST:
					routes[prefix].broadcast = handler.broadcast
				elif required == ROUTE:
					routes[prefix].route = reverse_routes[routes[prefix]]
				elif required == LAST_STOP:
					routes[prefix].last_stop = handler.last_stop
			routes[prefix].start()
	return routes