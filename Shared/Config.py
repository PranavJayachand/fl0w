from imp import load_source
from os.path import isfile
from marshal import dumps, loads
from types import FunctionType


class OptionDuplicateError(IndexError):
	def __init__(self, name):
		super(IndexError, self).__init__("'%s' already exists" % name)	


class OptionNotFoundError(IndexError):
	def __init__(self, name):
		super(IndexError, self).__init__("'%s' does not exist" % name)	


class NameMustBeStringError(Exception):
	def __init__(self):
		super(Exception, self).__init__("option names have to be strings")		


def make_value(value):
	if type(value) is str:
		value = '"%s"' % value
	elif type(value) in (list, tuple, dict):
		value = str(value)
	elif type(value) is FunctionType:
		value = dumps(value.__code__)
	return value


class Option:
	def __init__(self, name, default_value, validator=None, comment=""):
		if not type(name) is str:
			raise NameMustBeStringError()
		self.name = name
		self.default_value = default_value
		self.validator = validator
		self.comment = comment


class Config:
	def __init__(self, options=[], validation_failed=None, override_on_error=False):
		if type(options) in (list, tuple):
			for option in options:
				if not type(option) is Option:
					raise TypeError("all options must be of type Option")
		else:
			raise TypeError("options must be a list or tuple containing options of type Option")
		self.options = options
		self.validation_failed = validation_failed
		self.override_on_error = override_on_error


	def read_from_file(self, file):
		if isfile(file):
			config = load_source("config", file)
			error = False
			for option in self.options:
				# Make sure all options are avaliable
				if option.name not in dir(config):
					setattr(config, option.name, option.default_value)
					error = True
				else:
					# Make sure all validators pass
					if option.validator != None:
						value = getattr(config, option.name)
						if not option.validator(value):
							setattr(config, option.name, option.default_value)
							if self.validation_failed != None:
								self.validation_failed(option.name, value)
							error = True
				if self.override_on_error:
					if error:
						self.write_to_file(file)
			return config
		else:
			raise FileNotFoundError()


	def add(self, new_option):
		if type(new_option) is Option:
			for option in self.options:
				if new_option.name == option.name:
					raise OptionDuplicateError(option.name)
			self.options.append(new_option)
		else:
			raise TypeError("invalid type supplied")


	def remove(self, option):
		if option in self.options:
			del self.options[self.options.index(option)]
		else:
			raise OptionNotFoundError(option.name)


	def write_to_file(self, file):
		open(file, "w").write(self.get())


	def get(self):
		contains_function = False
		out = ""
		for option in self.options:
			value = make_value(option.default_value)
			if type(option.default_value) is FunctionType:
				if not contains_function:
					out = "from marshal import loads; from types import FunctionType\n\n" + out
					contains_function = True
				value = 'FunctionType(loads(%s), globals(), "%s")' % (value, option.name)
			out += "%s = %s%s\n" % (option.name, value, 
				(" # %s" % option.comment) if option.comment else "")
		return out	


	def __repr__(self):
		return self.get()