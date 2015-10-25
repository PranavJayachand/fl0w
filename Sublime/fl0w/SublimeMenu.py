class Input:
	def __init__(self, caption, initial_text="", on_done=None, on_change=None, on_cancel=None):
		self.caption = caption
		self.initial_text = initial_text
		self.on_done = on_done
		self.on_change = on_change
		self.on_cancel = on_cancel


	def invoke(self, window):
		window.show_input_panel(self.caption, self.initial_text, 
			self.on_done, self.on_change, self.on_cancel)


class Item:
	def __init__(self, name, description="", action=None, items=None, input=None):
		self.name = name
		self.description = description
		self.action = action
		self.items = items
		self.input = input

	def __eq__(self, other):
		return self.__dict__ == other.__dict__


class Items:
	def __init__(self, selected_index=-1, on_highlight=None):
		self.selected_index = selected_index
		self.on_highlight = on_highlight
		self.items = {}
		self.item_names = []
		self.window = None
		self.back = None

	def invoke(self, window, back=None):
		self.window = window
		if back:
			items = [["Back", "Back to previous menu"]] + self.item_names[:]
			print(items)
			self.back = back
		else:
			items = self.item_names
			self.back = None
		window.show_quick_panel(items, self._action, 
			flags=0, selected_index=self.selected_index, 
			on_highlight=self.on_highlight)

	def _action(self, item_id):
		if item_id != -1:
			if self.back:
				if item_id != 0:
					item = self.items[item_id - 1]
				else:
					self.back.invoke(self.window)
					return
			else:
				item = self.items[item_id]
			if item.action != None:
				item.action() 
			if item.input != None:
				item.input.invoke(self.window)
			if item.items != None:
				item.items.invoke(self.window, back=self)
					

	def add_item(self, item):
		if len(self.items) > 0:
			item_id = tuple(self.items.keys())[-1] + 1
		else:
			item_id = 0
		self.items[item_id] = item
		if item.description != None: 
			self.item_names.append([item.name, item.description])
		else:
			self.item_names.append([item.name, ""])

	def rm_item(self, item):
		if item in self.items.values():
			for i in self.items:
				if self.items[i] == item:
					del self.items[i]
					del self.item_names[i]
					return True
		return False