from imp import load_source
from os.path import isfile


class ValidationFailedError(Exception):
	def __init__(self, name):
		super(InputError, self).__init__("validation failed for '%s'" % name)


class OptionNotFoundError(IndexError):
	def __init__(self, name):
		super(InputError, self).__init__("'%s' does not exist" % name)	


def make_value(value):
	if type(value) is str:
		value = '"%s"' % value
	elif type(value) in (list, tuple, tuple):
		value = str(value)
	return value


class Option:
	def __init__(self, name, default_value, validator=None, comment=""):
		self.name = name
		self.default_value = default_value
		self.validator = validator
		self.comment = comment


class Config:
	def __init__(self, options=[]):
		self.options = options


	def read_from_file(self, file):
		if isfile(file):
			config = load_source("config", file)
			return config
		else:
			raise FileNotFoundError()


	def add(self, option):
		self.options.append(option)


	def remove(self, option):
		if option in self.options:
			del self.options[self.options.index(option)]
		else:
			raise OptionNotFoundError(option.name)


	def write_to_file(self, file):
		open(file, "w").write(self.get())


	def get(self):
		out = ""
		for option in self.options:
			out += "%s = %s %s\n" % (option.name, make_value(option.default_value), ("# %s" % option.comment) if option.comment else "")
		return out	


	def __repr__(self):
		return self.get()