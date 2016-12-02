FUNCTION = type(lambda: 1)

class Input:
	def __init__(self, caption, initial_text="", on_done=None, on_change=None,
			on_cancel=None, kwargs={}):
		self.caption = caption
		self.initial_text = initial_text
		self.on_done = on_done
		self.on_change = on_change
		self.on_cancel = on_cancel
		self.kwargs = kwargs


	def wrapped_on_done(self, input_):
		if not self.on_done == None:
			self.on_done(input_, **self.kwargs)


	def wrapped_on_change(self, input_):
		if not self.on_change == None:		
			self.on_change(input_, **self.kwargs)


	def wrapped_on_cancel(self):
		if not self.on_cancel == None:		
			self.on_cancel(**self.kwargs)


	def invoke(self, window):
		window.show_input_panel(self.caption, self.initial_text,
			self.wrapped_on_done, self.wrapped_on_change, 
			self.wrapped_on_cancel)


class Entry:
	def __init__(self, name, description="", action=None, kwargs={},
			sub_menu=None, input=None):
		self.name = name
		self.description = description
		self.action = action
		self.kwargs = kwargs
		self.sub_menu = sub_menu
		self.input = input

	def __eq__(self, other):
		return self.__dict__ == other.__dict__


class Menu:
	def __init__(self, selected_index=-1, on_highlight=None, subtitles=True):
		self.selected_index = selected_index
		self.on_highlight = on_highlight
		self.subtitles = subtitles
		self.entries = {}
		self.window = None
		self.back = None

	def invoke(self, window, back=None):
		self.window = window
		self.back = back
		entries = self.menu_entries
		if back:
			entries.insert(0, ["Back", "Back to previous menu"])
		if not self.subtitles:
			for entry_index in range(len(entries)):
				del entries[entry_index][1]
		window.show_quick_panel(entries, self._action,
			flags=0, selected_index=self.selected_index,
			on_highlight=self.on_highlight)

	def _action(self, entry_id):
		if entry_id != -1:
			if self.back:
				if entry_id != 0:
					entry = self.entries[entry_id - 1]
				else:
					self.back.invoke(self.window)
					return
			else:
				entry = self.entries[entry_id]
			if entry.action != None:
				entry.action(**entry.kwargs)
			if entry.input != None:
				entry.input.invoke(self.window)
			if type(entry.sub_menu) is FUNCTION:
				entry.sub_menu(entry).invoke(self.window, back=self)
			elif entry.sub_menu != None:
				entry.sub_menu.invoke(self.window, back=self)


	@property
	def menu_entries(self):
		entries = []
		for entry_id in self.entries:
			entries.append([self.entries[entry_id].name, self.entries[entry_id].description])
		return entries


	def __add__(self, other):
		try:
			self.add(other)
		except TypeError:
			return NotImplemented
		return self


	def __sub__(self, other):
		try:
			self.remove(other)
		except TypeError:
			return NotImplemented
		return self


	def add(self, entry):
		if entry.__class__ == Entry:
			if len(self.entries) > 0:
				entry_id = tuple(self.entries.keys())[-1] + 1
			else:
				entry_id = 0
			self.entries[entry_id] = entry
		else:
			raise TypeError("invalid type supplied")


	def remove(self, entry):
		if entry.__class__ == Entry:
			if entry in self.entries.values():
				found_entry_id = None
				for entry_id in self.entries:
					if self.entries[entry_id] == entry:
						found_entry_id = entry_id
				if found_entry_id != None:
					del self.entries[entry_id]
		else:
			raise TypeError("invalid type supplied")
