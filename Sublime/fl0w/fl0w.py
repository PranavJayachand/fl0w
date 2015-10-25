from sys import path
import os
path.append(os.path.dirname(os.path.realpath(__file__)))

import sublime 
import sublime_plugin
import random
from SublimeMenu import *


class Fl0w:
	def __init__(self):
		self.window = None
		self.main_menu = Items()
		self.link_menu = Items()
		self.link_menu.add_item(Item("Compile", action=self.info))
		self.main_menu.add_item(Item("Connect", "Connect to a fl0w server", action=self.connect))
		self.main_menu.add_item(Item("Set Link", items=self.link_menu))
		

	def info(self):
		sublime.message_dialog("No")

	def connect(self):
		Input("IP:Port", on_done=self.set_ip).invoke(self.window)
		Input("User:", on_done=self.set_ip).invoke(self.window)
		Input("Password:", on_done=self.set_ip).invoke(self.window)

	def set_ip(self, ip_pair):
		print(ip_pair)

	def authed(self):
		
		self.main_menu.add_item(Item("Compile", action=self.info))
		self.main_menu.add_item(Item("Resync", action=self.info))
		self.main_menu.add_item(Item("Disconnect", action=self.info))
		self.main_menu.add_item(Item("Backup", action=self.info))


class Fl0wCommand(sublime_plugin.WindowCommand):
	def run(self, menu=None, action=None): 
		if fl0w.window == None:
			fl0w.window = self.window
		fl0w.main_menu.invoke(self.window)

"""
def test():
	print("Testing :3")

def test_input(user_input):
	print(user_input)


item_handler = Items()
sub_item_handler = Items()

sub0_test = Item("Test", description="test", action=lol, items=sub_item_handler)
sub0_test1 = Item("Test1", action=test)
sub1_test1 = Item("Test1", action=test, input=Input("Test:", initial_text="Test", on_done=test_input))


sub_item_handler.add_item(sub1_test1)
item_handler.add_item(sub0_test)
item_handler.add_item(sub0_test1)
"""

fl0w = Fl0w()