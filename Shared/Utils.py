from traceback import print_exception
from sys import exc_info
import platform
import os
import struct
import socket
import fcntl

class HostnameNotChangedError(PermissionError):
	def __init__(self):
		super(PermissionError, self).__init__("hostname could not be changed")	

def capture_trace():
	exc_type, exc_value, exc_traceback = exc_info()
	print_exception(exc_type, exc_value, exc_traceback)


def is_wallaby():
	return "3.18.21-custom" in platform.uname().release


def is_linux():
	return platform.uname().system == "Linux"


def is_darwin():
	return platform.uname().system == "Darwin"


def is_windows():
	return platform.uname().system == "Windows"	


def set_hostname(hostname):
	if is_linux():
		if os.geteuid() == 0:
			open("/etc/hostname", "w").write(hostname)
		else:
			raise HostnameNotChangedError()
	elif is_darwin():
		if os.geteuid() == 0:
			subprocess.check_call(["scutil", "--set", "HostName", hostname])
		else:
			raise HostnameNotChangedError()
	else:
		raise HostnameNotChangedError()


def get_hostname():
	return platform.uname().node


def get_ip_address(ifname=None):
	if ifname:
		if is_linux():
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			try:
				return socket.inet_ntoa(fcntl.ioctl(
				s.fileno(),
				0x8915,  # SIOCGIFADDR
				struct.pack('256s', ifname[:15].encode()))[20:24])
			except OSError:
				pass
	else:
		if is_darwin() or is_windows():
			return socket.gethostbyname(socket.gethostname())
		if is_linux():
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.connect(('8.8.8.8', 53))
			ip_address = sock.getsockname()[0]
			sock.close()
			return ip_address
