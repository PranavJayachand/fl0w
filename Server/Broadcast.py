class Broadcast:
	def __init__(self):
		self.socks = []

	def broadcast(self, data, exclude=[]):
		for sock in self.socks:
			if not sock in exclude:
				sock.send(data)

	def remove(self, sock):
		if sock in self.socks:
			del self.socks[self.socks.index(sock)]

	def add(self, sock):
		if not sock in self.socks:
			self.socks.append(sock)