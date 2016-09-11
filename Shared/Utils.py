from traceback import print_exception
from sys import exc_info
import platform

def capture_trace():
	exc_type, exc_value, exc_traceback = exc_info()
	print_exception(exc_type, exc_value, exc_traceback)


def is_wallaby():
	return "3.18.21-custom" in platform.uname().release