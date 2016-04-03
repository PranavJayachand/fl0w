from traceback import print_exception
from sys import exc_info
from platform import uname

def capture_trace():
	exc_type, exc_value, exc_traceback = exc_info()
	print_exception(exc_type, exc_value, exc_traceback)

def is_socket_related_error(error):
	if type(error) not in (BrokenPipeError, ConnectionResetError, OSError):
		return False
	if type(error) is OSError:
		if str(error) not in ("Connection closed", "[Errno 9] Bad file descriptor"):
			return False
	return True

def is_wallaby():
	return "ARMv7" in uname()