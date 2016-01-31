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


class Entry:
	def __init__(self, name, description="", action=None, kwargs={}, sub_menu=None, input=None):
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
			if entry.sub_menu != None:
				entry.sub_menu.invoke(self.window, back=self)

	@property
	def menu_entries(self):
		entries = []
		for entry_id in self.entries:
			entries.append([self.entries[entry_id].name, self.entries[entry_id].description])
		return entries
					

	def add(self, entry):
		if len(self.entries) > 0:
			entry_id = tuple(self.entries.keys())[-1] + 1
		else:
			entry_id = 0
		self.entries[entry_id] = entry


	def remove(self, entry):
		if entry in self.entries.values():
			for entry_id in self.entries:
				if self.entries[entry_id] == entry:
					del self.entries[entry_id]
