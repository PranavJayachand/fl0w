class Broadcast:
	class ChannelError(IndexError):
		def __init__(self, channel):
			super(Broadcast.ChannelError, self).__init__("channel '%s' does not exist" % channel)

	def __init__(self):
		self.channels = {}

	def broadcast(self, data, route, channel, exclude=[]):
		if channel in self.channels:
			for sock in self.channels[channel]:
				if not sock in exclude:
					sock.send(data, route)
		else:
			raise Broadcast.ChannelError(channel)

	def remove(self, sock, channel):
		if channel in self.channels:
			if sock in self.channels[channel]:
				del self.channels[channel][self.channels[channel].index(sock)]
		else:
			raise Broadcast.ChannelError(channel)

	def add(self, sock, channel):
		if channel in self.channels:
			if not sock in self.channels[channel]:
				self.channels[channel].append(sock)
		else:
			raise Broadcast.ChannelError(channel)

	def add_channel(self, channel):
		self.channels[channel] = []

	def remove_channel(self, channel):
		if channel in self.channels:
			del self.channels[channel]
		else:
			raise Broadcast.ChannelError(channel)

	def __repr__(self):
		out = "Channels:\n"
		for channel in self.channels:
			out += "%s: %d socks\n" % (channel, len(self.channels[channel]))
		return out.rstrip("\n")

	def __str__(self):
		return self.__repr__()