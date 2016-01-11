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

def create_routes(routes):
	routes = routes.copy()
	for prefix in routes:
		if type(routes[prefix]) is tuple or type(routes[prefix]) is list:
			routes[prefix] = routes[prefix][0](**routes[prefix][1])
	return routes