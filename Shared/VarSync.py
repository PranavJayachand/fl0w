import Routing

def check_value(value):
	if value is None:
		return True
	return type(value) in (dict, list, tuple, str, int, float, bool)


class Attribute:
	def __init__(self, value, change_callback):
		if check_value(value):
			self.value = value
		else:
			raise AttributeError("Unsupported data type (dict, list, tuple, str, int, float, bool)")
		self.change_callback = change_callback

	def __get__(self, instance, owner=None):
		return self.value

	def __set__(self, instance, value):
		if check_value(value):
			if not value is self.value:
				self.change_callback(self)
				self.value = value
		else:
			raise AttributeError("Unsupported data type (dict, list, tuple, str, int, float, bool)")



class Shared:
	def _attr_changed(self, changed_attr):
		attr_name = self.search_attr_name(changed_attr)
		if attr_name != None:
			self.sock.send({"set" : {attr_name : changed_attr.value}}, "varsync")


	def __getattr__(self, attr):
		if attr not in ("run", "setup", "sock", "attrs"):
			if attr in self.attrs:
				return self.attrs[attr]
			else:
				new_attr = Attribute(None, self._attr_changed)
				self.attrs[attr] = new_attr
				return new_attr
		else:
			return getattr(self, attr)


	def search_attr_name(self, attr):
		for attr_name in self.attrs:
			if self.attrs[attr_name] is attr:
				return attr_name
		return None


class Client(Routing.ClientRoute, Shared):
	def __init__(self, sock):
		self.sock = sock
		self.attrs = {}
		self.sock.send("sync", "varsync")


	def run(self, data, handler):
		if type(data) is dict:
			if "set" in data:
				for attr_name in data["set"]:
					self.attrs.append(Attribute(data["set"][attr_name]), "varsync")


class Server(Routing.ServerRoute, Shared):
	def setup(self, **kwargs):
		self.attrs = {}


	def run(self, data, handler):
		self.sock = handler.sock
		if data == "sync":
			handler.sock.send({"set" : self.attrs}, "varsync")
		if type(data) is dict:
			if "set" in data:
				for attr_name in data["set"]:
					if attr_name in self.attrs:
						self.attrs[attr_name] = data["set"][attr_name]
					else:
						self.attrs[attr_name] = Attribute(data["set"][attr_name], self._attr_changed)
					Logging.info("'%s' = '%s'" % (attr_name, str(data["set"][attr_name])))
		