class Route:
	def run(self, data, handler):
		pass

	def start(self, handler):
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


def create_exchange_map(routes):
	exchange_map = {0 : "meta"}
	exchange_id = 1
	for route in routes:
		if route != "meta":
			exchange_map[exchange_id] = route
			exchange_id += 1
	return exchange_map


def validate_exchange_map(routes):
	for key in routes:
		if not type(key) is int and type(routes[key]) is str:
			return False
	return True